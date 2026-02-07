"""
crawler for GitLab Handbook pages.

What it does:
- Starts from seed URLs (default: People, Finance, Security, Legal sections)
- Stays within about.gitlab.com/handbook/
- Fetches pages with retries + timeouts
- Saves raw HTML to data/raw/pages/
- Appends crawl metadata to data/raw/manifest.jsonl
- Skips already-downloaded URLs 

Run:
  python -m ingestion.crawler

Or with custom settings:
  python -m ingestion.crawler --max-pages 80 --concurrency 4 --delay 0.7
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from ingestion.config import *

@dataclass(frozen=True)
class CrawlConfig:
    out_dir: Path
    pages_dir: Path
    manifest_path: Path
    max_pages: int
    concurrency: int
    timeout_s: float
    retries: int
    delay_s: float
    jitter_s: float
    user_agent: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_url(url: str) -> str:
    """
    Normalize URL to reduce duplicates:
    - force https
    - drop fragments
    - remove trailing slash normalization (keep trailing slash for handbook pages)
    - drop common tracking query params
    """
    url = url.strip()
    if not url:
        return url

    parsed = urlparse(url)
    scheme = "https"
    netloc = parsed.netloc or ALLOWED_HOST

    # Drop fragment
    fragment = ""

    # Keep only "safe" query params (GitLab handbook usually doesn't need any)
    query = ""
    path = parsed.path

    # Normalize path: handbook pages often end with '/'
    # Keep it as-is; but if path is exactly '/handbook' -> '/handbook/'
    if path == "/handbook":
        path = "/handbook/"

    return urlunparse((scheme, netloc, path, "", query, fragment))


def is_allowed(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False

    if p.netloc != ALLOWED_HOST:
        return False
    if not p.path.startswith(ALLOWED_PREFIX):
        return False

    # Avoid non-HTML assets
    if re.search(r"\.(png|jpg|jpeg|gif|svg|webp|css|js|pdf|zip|mp4|mov|webm)$", p.path, re.I):
        return False

    return True


def classify_section(url: str) -> str:
    path = urlparse(url).path
    # crude but useful
    if "/handbook/finance/" in path:
        return "finance"
    if "/handbook/security/" in path:
        return "security"
    if "/handbook/legal/" in path:
        return "legal"
    if "/handbook/people-group/" in path:
        return "people-group"
    return "handbook"


def safe_filename_from_url(url: str) -> str:
    """
    Create a stable filename for a URL:
    - Use last path segment or 'index'
    - Add short hash to avoid collisions
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    parts = path.split("/")
    last = parts[-1] if parts and parts[-1] else "index"

    # slugify
    last = re.sub(r"[^a-zA-Z0-9\-_.]+", "-", last).strip("-").lower()
    if not last:
        last = "index"

    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{last}-{h}.html"


def load_existing_manifest_urls(manifest_path: Path) -> set[str]:
    if not manifest_path.exists():
        return set()

    urls: set[str] = set()
    with manifest_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                u = rec.get("url")
                if isinstance(u, str) and u:
                    urls.add(u)
            except Exception:
                continue
    return urls


def extract_links(base_url: str, html: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")

    links: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href:
            continue

        # Join relative URLs
        abs_url = urljoin(base_url, href)
        abs_url = normalize_url(abs_url)

        if is_allowed(abs_url):
            links.add(abs_url)

    return links


async def fetch_with_retries(
    client: httpx.AsyncClient,
    url: str,
    cfg: CrawlConfig,
) -> Optional[str]:
    for attempt in range(cfg.retries + 1):
        try:
            r = await client.get(url, timeout=cfg.timeout_s, follow_redirects=True)
            if r.status_code == 200 and "text/html" in (r.headers.get("content-type") or ""):
                return r.text
            # Treat 4xx/5xx as non-fatal, but don't retry too aggressively
        except (httpx.TimeoutException, httpx.TransportError):
            pass

        if attempt < cfg.retries:
            # exponential-ish backoff with jitter
            backoff = (0.6 * (2 ** attempt)) + random.uniform(0, cfg.jitter_s)
            await asyncio.sleep(backoff)

    return None


async def worker(
    name: str,
    queue: asyncio.Queue[str],
    seen: set[str],
    seen_lock: asyncio.Lock,
    cfg: CrawlConfig,
    client: httpx.AsyncClient,
    discovered: "asyncio.Queue[str]",
) -> None:
    while True:
        url = await queue.get()
        try:
            # Polite delay between requests
            await asyncio.sleep(cfg.delay_s + random.uniform(0, cfg.jitter_s))

            html = await fetch_with_retries(client, url, cfg)
            if html is None:
                # Log a failure record (optional)
                rec = {
                    "url": url,
                    "status": "failed",
                    "fetched_at": utc_now_iso(),
                    "section": classify_section(url),
                }
                cfg.manifest_path.parent.mkdir(parents=True, exist_ok=True)
                with cfg.manifest_path.open("a", encoding="utf-8") as mf:
                    mf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                continue

            # Save HTML
            cfg.pages_dir.mkdir(parents=True, exist_ok=True)
            filename = safe_filename_from_url(url)
            out_path = cfg.pages_dir / filename
            out_path.write_text(html, encoding="utf-8")

            # Manifest record
            rec = {
                "url": url,
                "status": "ok",
                "path": str(out_path),
                "fetched_at": utc_now_iso(),
                "section": classify_section(url),
                "bytes": len(html.encode("utf-8")),
            }
            cfg.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with cfg.manifest_path.open("a", encoding="utf-8") as mf:
                mf.write(json.dumps(rec, ensure_ascii=False) + "\n")

            # Extract and enqueue discovered links
            new_links = extract_links(url, html)

            # De-dup with lock
            async with seen_lock:
                for link in new_links:
                    if link not in seen and len(seen) < cfg.max_pages:
                        seen.add(link)
                        await discovered.put(link)

        finally:
            queue.task_done()


async def crawl(seeds: Iterable[str], cfg: CrawlConfig) -> None:
    # Load already crawled URLs from manifest (resume-safe)
    crawled_urls = load_existing_manifest_urls(cfg.manifest_path)

    # Seen = already crawled + seeds discovered
    seen: set[str] = set(crawled_urls)
    seen_lock = asyncio.Lock()

    # Work queues
    queue: asyncio.Queue[str] = asyncio.Queue()
    discovered: asyncio.Queue[str] = asyncio.Queue()

    # Seed
    normalized_seeds = [normalize_url(s) for s in seeds if s]
    for s in normalized_seeds:
        if is_allowed(s) and s not in seen and len(seen) < cfg.max_pages:
            seen.add(s)
            await discovered.put(s)

    # Prepare HTTP client
    headers = {"User-Agent": cfg.user_agent}
    limits = httpx.Limits(max_keepalive_connections=cfg.concurrency, max_connections=cfg.concurrency)

    async with httpx.AsyncClient(headers=headers, limits=limits) as client:
        # Start workers
        workers = [
            asyncio.create_task(worker(f"w{i}", queue, seen, seen_lock, cfg, client, discovered))
            for i in range(cfg.concurrency)
        ]

        # Scheduler loop: move from discovered -> queue until max_pages reached
        scheduled = 0
        start_time = time.time()

        try:
            while True:
                # Stop when we've scheduled enough pages
                if scheduled >= cfg.max_pages:
                    break

                # If nothing new is discovered and queue is empty, we're done
                if discovered.empty() and queue.empty():
                    break

                # Pull from discovered queue and push into work queue
                try:
                    next_url = await asyncio.wait_for(discovered.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue

                # Skip if already crawled earlier (manifest) and file exists? (we keep simple)
                if next_url in crawled_urls:
                    discovered.task_done()
                    continue

                await queue.put(next_url)
                discovered.task_done()
                scheduled += 1

                if scheduled % 10 == 0:
                    elapsed = int(time.time() - start_time)
                    print(f"[crawler] scheduled={scheduled}/{cfg.max_pages} seen={len(seen)} elapsed={elapsed}s")

            # Wait for work to finish
            await queue.join()

        finally:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

    print(f"[crawler] done. crawled={scheduled} total_seen={len(seen)} manifest={cfg.manifest_path}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crawl GitLab Handbook sections and save raw HTML.")
    p.add_argument("--out-dir", type=str, default="data/raw", help="Base output directory.")
    p.add_argument("--max-pages", type=int, default=80, help="Maximum pages to crawl (excluding already-crawled).")
    p.add_argument("--concurrency", type=int, default=4, help="Parallel request workers.")
    p.add_argument("--timeout", type=float, default=10.0, help="Request timeout seconds.")
    p.add_argument("--retries", type=int, default=2, help="Retries per URL on transient failures.")
    p.add_argument("--delay", type=float, default=0.7, help="Base polite delay between requests (seconds).")
    p.add_argument("--jitter", type=float, default=0.5, help="Random jitter added to delays/backoff (seconds).")
    p.add_argument(
        "--user-agent",
        type=str,
        default="rag-service-bot/1.0 (contact: you@example.com)",
        help="User-Agent header. Set a real contact if you want.",
    )
    p.add_argument(
        "--seeds",
        type=str,
        nargs="*",
        default=DEFAULT_SEEDS,
        help="Seed URLs to start crawling from.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    pages_dir = out_dir / "pages"
    manifest_path = out_dir / "manifest.jsonl"

    cfg = CrawlConfig(
        out_dir=out_dir,
        pages_dir=pages_dir,
        manifest_path=manifest_path,
        max_pages=int(args.max_pages),
        concurrency=int(args.concurrency),
        timeout_s=float(args.timeout),
        retries=int(args.retries),
        delay_s=float(args.delay),
        jitter_s=float(args.jitter),
        user_agent=str(args.user_agent),
    )

    # Ensure dirs exist
    cfg.pages_dir.mkdir(parents=True, exist_ok=True)
    cfg.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    # Normalize seeds
    seeds = [normalize_url(s) for s in args.seeds]
    seeds = [s for s in seeds if is_allowed(s)]

    if not seeds:
        raise SystemExit("No valid seed URLs. Provide --seeds under https://about.gitlab.com/handbook/")

    asyncio.run(crawl(seeds, cfg))


if __name__ == "__main__":
    main()
