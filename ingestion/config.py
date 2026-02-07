
DEFAULT_SEEDS = [
    "https://about.gitlab.com/handbook/people-group/",
    "https://about.gitlab.com/handbook/finance/",
    "https://about.gitlab.com/handbook/security/",
    "https://about.gitlab.com/handbook/legal/",
]

ALLOWED_HOST = "about.gitlab.com"
ALLOWED_PREFIX = "/handbook/"

REQUEST_TIMEOUT = 10
MAX_RETRIES = 3

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
