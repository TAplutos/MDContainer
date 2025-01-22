from starlette.testclient import TestClient
import asyncio


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

async def make_request(testclient: TestClient, data):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: testclient.post("/evaluate", json=data))


def test_evaluate(testclient: TestClient):
    # Input data for the test
    data = {"code": "return x * x", "scope": {"x": 2}, "language": "python"}

    # Run two requests simultaneously
    async def run_test():
        responses = await asyncio.gather(
            make_request(testclient, data),
            make_request(testclient, data),
        )

        # Assertions for both responses
        for response in responses:
            assert response.status_code == 200, response.text
            assert "output" in response.json()
            assert response.json()["output"] == 4  # Adjust based on your endpoint logic

    # Run the async test function
    asyncio.run(run_test())


def test_evaluate_fail(testclient: TestClient):
    # Input data for the test
    data = {"code": "returnn 1+1", "language": "python"}

    # Send a POST request to the root endpoint
    response = testclient.post("/evaluate", json=data)

    # Assertions
    assert "error" in response.json()


def test_evaluate_fail_javascript(testclient: TestClient):
    # Input data for the test
    data = {"code": "returnn 1+1", "language": "python"}

    # Send a POST request to the root endpoint
    response = testclient.post("/evaluate", json=data)

    # Assertions
    assert "error" in response.json()


def test_evaluate_javascript(testclient: TestClient):
    # Input data for the test
    data = {"code": "return 1+x;", "scope": {"x": 2}, "language": "javascript"}

    # Send a POST request to the root endpoint
    response = testclient.post("/evaluate", json=data)

    # Assertions
    assert response.status_code == 200, response.text
    assert "output" in response.json()
    assert response.json()["output"] == 3  # Adjust based on your endpoint logic
