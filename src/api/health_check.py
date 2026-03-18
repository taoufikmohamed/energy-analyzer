def check_api_health():
    try:
        response = requests.get(f"{EIA_API_BASE_URL}/health")
        return response.status_code == 200
    except:
        return False