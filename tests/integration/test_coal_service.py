import pytest
from src.services.coal_service import fetch_coal_data
from src.services.fallback_service import FallbackService

@pytest.mark.integration
def test_coal_service_integration():
    result = fetch_coal_data()
    
    assert result is not None
    assert 'timestamp' in result
    assert 'source' in result
    assert 'status' in result
    
    if result['source'] == 'fallback':
        assert result['status'] == 'degraded'