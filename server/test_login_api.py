import urllib.request
import json

def test_login(url, user, pwd):
    try:
        data = json.dumps({'email': user, 'password': pwd}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        res = urllib.request.urlopen(req)
        parsed = json.loads(res.read().decode('utf-8'))
        print(f"SUCCESS [200 OK] {url} -> User: {parsed['user']['name']} ({parsed['user']['email']}), Role: {parsed['user']['role']}")
        return True
    except Exception as e:
        print(f"FAILED {url} with {user}/{pwd}: {e}")
        return False

if __name__ == '__main__':
    print("--- TESTING LOGIN API ENDPOINTS ---")
    test_login('http://127.0.0.1:8000/auth/login', 'admin', 'admin123')
    test_login('http://127.0.0.1:8000/auth/login', 'admin', 'password123')
    test_login('http://127.0.0.1:8000/api/auth/login', 'admin@forensics.gov', 'password123')
    test_login('http://127.0.0.1:8000/api/auth/login', 'admin@forensics.gov', 'admin123')
    test_login('http://127.0.0.1:8000/api/auth/login', 'investigator', 'password123')
    test_login('http://127.0.0.1:8000/api/auth/login', 'viewer', 'password123')
