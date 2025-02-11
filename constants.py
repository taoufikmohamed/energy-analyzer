"""API Configuration Constants"""

# API Endpoints
EIA_API_BASE_URL = "https://api.eia.gov/v2"
DEEPSEEK_API_BASE_URL = "https://api.deepseek.com/v1"
EIA_ENDPOINT = f"{EIA_API_BASE_URL}/electricity/rto/generation-type/data"
DEEPSEEK_ENDPOINT = f"{DEEPSEEK_API_BASE_URL}/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# API Timeouts (seconds)
CONNECT_TIMEOUT = 5  # Reduced timeout for faster failure detection
READ_TIMEOUT = 15    # Reduced timeout for quicker response
MAX_RETRY_TIME = 30  # Reduced max retry time

# Retry Configuration
MAX_RETRIES = 3
RETRY_BACKOFF = 0.5  # Reduced backoff for faster retries
RETRY_STATUS_CODES = [408, 429, 500, 502, 503, 504]
RETRY_DELAY = 1  # Reduced delay between retries

# Cache Configuration
CACHE_DURATION = 300  # 5 minutes
MAX_CACHE_ITEMS = 1000

# Request Headers
DEFAULT_HEADERS = {
    'User-Agent': 'EnergyAnalytics/1.0',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Connection': 'keep-alive',  # Added for connection reuse
    'Keep-Alive': 'timeout=5, max=1000'  # Added connection keep-alive settings
}

# Fallback Configuration
FALLBACK_ENABLED = True  # Enable fallback responses
FALLBACK_CACHE_DURATION = 600  # 10 minutes for fallback data

# Energy Sources
ENERGY_SOURCES = {
    'Solar': {'base_prod': 1000, 'base_cost': 0.1},
    'Wind': {'base_prod': 800, 'base_cost': 0.08},
    'Coal': {'base_prod': 500, 'base_cost': 0.15},
    'Natural Gas': {'base_prod': 600, 'base_cost': 0.12}
}

# Error Messages
ERROR_MESSAGES = {
    'network': "Network error occurred. Please check your internet connection.",
    'timeout': "Request timed out. Please try again.",
    'auth': "Authentication failed. Please check your API keys.",
    'rate_limit': "Rate limit exceeded. Please try again later.",
    'server': "Server error occurred. Please try again later.",
    'unknown': "An unexpected error occurred. Please try again."
}