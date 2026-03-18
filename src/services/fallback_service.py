from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FallbackService:
    def __init__(self):
        self.cached_values = {}
        self.fallback_thresholds = {
            'coal': {'min': 400, 'max': 600},
            'natural_gas': {'min': 500, 'max': 700}
        }

    def get_fallback_data(self, source_type):
        logger.info(f"Initiating fallback for {source_type}")
        
        fallback_data = {
            'timestamp': datetime.now().isoformat(),
            'source': 'fallback',
            'status': 'degraded',
            'values': self._get_latest_cached_values(source_type)
        }
        
        logger.debug(f"Fallback data generated for {source_type}: {fallback_data}")
        return fallback_data

    def _get_latest_cached_values(self, source_type):
        if source_type not in self.cached_values:
            # Return default values if no cache exists
            return self._get_default_values(source_type)
        return self.cached_values[source_type]

    def _get_default_values(self, source_type):
        thresholds = self.fallback_thresholds.get(source_type, {'min': 0, 'max': 100})
        return {
            'production': thresholds['min'],
            'capacity': thresholds['max'],
            'reliability': 'unknown'
        }