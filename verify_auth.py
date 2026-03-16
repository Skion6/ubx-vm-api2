import sys
import unittest
from fastapi.testclient import TestClient

# Mock docker before importing app if necessary, but since we are just testing auth, 
# we can try to import directly and see if it fails on initialization.
try:
    from main import app, ADMIN_PASSWORD
except Exception as e:
    print(f"Error importing app: {e}")
    # If it fails due to Docker, we might need to mock it.
    # For now, let's assume it might work if docker is running or if we mock the client.
    sys.exit(1)

client = TestClient(app)

class TestAuth(unittest.TestCase):
    def test_list_vms_no_password(self):
        response = client.get("/api/list")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Unauthorized: Invalid or missing password"})

    def test_list_vms_wrong_password(self):
        response = client.get("/api/list?password=wrong")
        self.assertEqual(response.status_code, 401)

    def test_list_vms_correct_password_query(self):
        # This might still fail if Docker client isn't running, but we want to see the 401 vs something else
        response = client.get(f"/api/list?password={ADMIN_PASSWORD}")
        # If it's 500/Docker error, at least it's not 401
        self.assertNotEqual(response.status_code, 401)

    def test_list_vms_correct_password_header(self):
        response = client.get("/api/list", headers={"X-Admin-Password": ADMIN_PASSWORD})
        self.assertNotEqual(response.status_code, 401)

    def test_delete_vm_no_password(self):
        response = client.get("/api/delete/test-id")
        self.assertEqual(response.status_code, 401)

    def test_delete_vm_correct_password(self):
        response = client.get(f"/api/delete/test-id?password={ADMIN_PASSWORD}")
        self.assertNotEqual(response.status_code, 401)

if __name__ == "__main__":
    unittest.main()
