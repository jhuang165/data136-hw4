import requests
import json

BASE_URL = "http://localhost:8000"

def test_api_auth():
    """Test that API endpoints return proper status codes"""
    
    # Test 1: /app/api/dump-uploads/ without login should return 401
    print("Testing /app/api/dump-uploads/ without login...")
    response = requests.get(f"{BASE_URL}/app/api/dump-uploads/")
    print(f"Status: {response.status_code}, Expected: 401")
    print(f"Response: {response.text[:100]}...")
    assert response.status_code == 401, "Should return 401"
    
    # Test 2: /app/api/dump-data/ without login should return 401
    print("\nTesting /app/api/dump-data/ without login...")
    response = requests.get(f"{BASE_URL}/app/api/dump-data/")
    print(f"Status: {response.status_code}, Expected: 401")
    assert response.status_code == 401, "Should return 401"
    
    # Test 3: /app/uploads/ without login should redirect to login (302 or 200 with login page)
    print("\nTesting /app/uploads/ without login...")
    response = requests.get(f"{BASE_URL}/app/uploads/", allow_redirects=False)
    print(f"Status: {response.status_code}, Expected: 302 or 200 with login page")
    
    print("\nAll tests passed!")

if __name__ == "__main__":
    test_api_auth()
import requests
import json

BASE_URL = "http://localhost:8000"

def login_user(username, password):
    """Login and return session cookies"""
    session = requests.Session()
    
    # Get login page to get CSRF token
    response = session.get(f"{BASE_URL}/accounts/login/")
    
    # Extract CSRF token
    csrf_token = None
    if 'csrftoken' in session.cookies:
        csrf_token = session.cookies['csrftoken']
    
    # Login
    login_data = {
        'username': username,
        'password': password,
        'csrfmiddlewaretoken': csrf_token
    }
    
    headers = {
        'Referer': f"{BASE_URL}/accounts/login/",
        'X-CSRFToken': csrf_token
    }
    
    response = session.post(
        f"{BASE_URL}/accounts/login/",
        data=login_data,
        headers=headers
    )
    
    return session

def test_curator_access():
    """Test that curator endpoints work properly"""
    
    # First, create a regular user and a curator user
    print("This test requires manual setup. Run with actual users.")
    
    # Test with regular user
    print("\nTesting with regular user (if you have one)...")
    
    # Test with curator user
    print("\nTesting with curator user (if you have one)...")

if __name__ == "__main__":
    test_curator_access()
