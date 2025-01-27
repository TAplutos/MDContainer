from starlette.testclient import TestClient

def test_root_endpoint(testclient: TestClient):
    r = testclient.get("/")
    assert r.status_code == 200


def test_update_item(testclient: TestClient):
    data = {"name": "New Item", "price": "0.38", "is_offer": True}
    r = testclient.put("/items/1", json=data)
    assert r.status_code == 200, r.text
    assert r.json()["item_name"] == data["name"]


def test_read_item(testclient: TestClient):
    r = testclient.get("/items/1", params={"q": "query"})
    assert r.status_code == 200, r.text
    assert r.json()["item_id"] == 1


def test_evaluate(testclient: TestClient):
    # Input data for the test
    data = {"code": "return x * x", "scope" : {'x' : 2}, "dates" : {}, "language": "python"}

    # Send a POST request to the root endpoint
    response = testclient.post("/evaluate", json=data)

    # Assertions
    assert response.status_code == 200, response.text
    assert "output" in response.json()
    assert response.json()["output"] == 4  # Adjust based on your endpoint logic


def test_evaluate_fail(testclient: TestClient):
    # Input data for the test
    data = {"code": """import os

def execute_command_with_execve(command, args, env_vars=None):
    if not env_vars:
        env_vars = os.environ  # Use the current environment if none is provided

    try:
        print(f"Executing command: {command} with args: {args} and env_vars: {env_vars}")
        os.execve(command, args, env_vars)
        return 0
    except FileNotFoundError:
        print(f"Command not found: {command}")
    except PermissionError:
        print(f"Permission denied: {command}")
    except Exception as e:
        print(f"An error occurred: {e}")
""", "language": "python"}

    # Send a POST request to the root endpoint
    response = testclient.post("/evaluate", json=data)

    # Assertions
    print(response.json())
    assert "error" in response.json()
    print("\n\n" + response.json()["error"])

def test_evaluate_fail_javascript(testclient: TestClient):
    # Input data for the test
    data = {"code": "returnn 1+1", "language": "python"}

    # Send a POST request to the root endpoint
    response = testclient.post("/evaluate", json=data)

    # Assertions
    assert "error" in response.json()
    print("\n\n" + response.json()["error"])

def test_evaluate_javascript(testclient: TestClient):
    # Input data for the test
    data = {"code": "return 1+x;", "scope" : {'x' : 2}, "language": "javascript"}

    # Send a POST request to the root endpoint
    response = testclient.post("/evaluate", json=data)

    # Assertions
    assert response.status_code == 200, response.text
    assert "output" in response.json()
    assert response.json()["output"] == 3  # Adjust based on your endpoint logic
    print("asdfasdf", response.text)