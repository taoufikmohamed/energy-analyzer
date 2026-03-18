import requests
import json
import threading
import time
import os
import logging

# Configure logger for this module
logger = logging.getLogger(__name__)

class EIAClient:
    def fetch_natural_gas_data(self, retries=3, delay=2):
        for attempt in range(retries):
            try:
                response = self._make_request(
                    endpoint=self.NATURAL_GAS_ENDPOINT,
                    params=self.default_params
                )
                if response.status_code == 200:
                    return response.json()
                
                # Use exponential backoff
                wait_time = delay * (2 ** attempt)
                time.sleep(wait_time)
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                
        # If all retries fail, use cached data
        return self._get_cached_data('natural_gas')