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
