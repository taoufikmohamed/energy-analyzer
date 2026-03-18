import logging
from datetime import datetime, timedelta

class ErrorMonitor:
    def __init__(self):
        self.error_counts = {}
        self.error_threshold = 3
        self.time_window = timedelta(minutes=5)

    def record_error(self, source_type, error_code):
        current_time = datetime.now()
        if source_type not in self.error_counts:
            self.error_counts[source_type] = []
        
        self.error_counts[source_type].append({
            'timestamp': current_time,
            'error_code': error_code
        })
        
        self._clean_old_errors(source_type)
        return self._should_activate_fallback(source_type)

    def _clean_old_errors(self, source_type):
        current_time = datetime.now()
        self.error_counts[source_type] = [
            error for error in self.error_counts[source_type]
            if current_time - error['timestamp'] <= self.time_window
        ]

    def _should_activate_fallback(self, source_type):
        return len(self.error_counts.get(source_type, [])) >= self.error_threshold