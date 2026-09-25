from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200


def test_order_lookup():
    response = client.post(
        "/chat",
        json={
            "customer_id": "cust_1",
            "message": "what is the status of ord_1"
        }
    )

    assert response.status_code == 200
    assert response.json()["escalate"] is False
    assert "shipped" in response.json()["answer"].lower()



def test_unknown_question():
    response = client.post(
        "/chat",
        json= {
            "customer_id": "cust_1",
            "message": "can i change my billing address?"
        }
    )

    assert response.status_code == 200
    assert response.json()["escalate"] is True



