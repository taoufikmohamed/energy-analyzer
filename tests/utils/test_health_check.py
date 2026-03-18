import pytest
import requests
from unittest.mock import Mock, patch
from src.utils.health_check import check_source_health, fetch_coal_data
from src.services.fallback_service import FallbackService

@pytest.fixture
def mock_response():
    return Mock(spec=requests.Response)

@pytest.fixture
def fallback_service():
    return FallbackService()

class TestHealthCheck:
    @patch('requests.get')
    def test_successful_health_check(self, mock_get, mock_response):
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = check_source_health('coal')
        assert result is True

    @patch('requests.get')
    def test_failed_health_check(self, mock_get, mock_response):
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = check_source_health('coal')
        assert result is False

    @patch('requests.get')
    def test_timeout_health_check(self, mock_get):
        mock_get.side_effect = requests.Timeout()
        
        result = check_source_health('coal')
        assert result is False

class TestCoalDataFetch:
    @patch('src.utils.health_check.check_source_health')
    def test_failed_health_check_returns_fallback(self, mock_health_check, fallback_service):
        mock_health_check.return_value = False
        
        result = fetch_coal_data()
        assert result['source'] == 'fallback'
        assert result['status'] == 'degraded'