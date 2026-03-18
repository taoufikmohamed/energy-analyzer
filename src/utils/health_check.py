import requests
import logging
from constants import EIA_API_BASE_URL
from src.utils.error_monitor import ErrorMonitor
from src.utils.health_check import check_source_health
from src.services.fallback_service import FallbackService

logger = logging.getLogger(__name__)

error_monitor = ErrorMonitor()
fallback_service = FallbackService()

def check_source_health(source_type):
    try:
        endpoint = f"{EIA_API_BASE_URL}/status/{source_type}"
        response = requests.get(
            endpoint,
            timeout=5,
            headers={'Accept': 'application/json'}
        )
        
        if response.status_code == 200:
            logger.info(f"Health check passed for {source_type}")
            return True
            
        logger.warning(f"Health check failed for {source_type}: {response.status_code}")
        return False
        
    except Exception as e:
        logger.error(f"Health check error for {source_type}: {str(e)}")
        return False

def fetch_coal_data():
    if not check_source_health('coal'):
        logger.warning("Coal API health check failed")
        return fallback_service.get_fallback_data('coal')

    try:
        # Your existing API call code here
        pass
    except Exception as e:
        if error_monitor.record_error('coal', 500):
            logger.error("Switching to fallback mode for coal data")
            return fallback_service.get_fallback_data('coal')
        raise