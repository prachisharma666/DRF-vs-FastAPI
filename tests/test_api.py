import os, httpx, pytest
BASE = os.environ["BASE_URL"]

def test_health():
    assert httpx.get(f"{BASE}/health").json() == {"status": "ok"}

@pytest.mark.parametrize("payload", [
    {},                                                        # missing fields
    {"work_id": "bad", "status": "reading"},                   # bad regex
    {"work_id": "OL1W", "status": "nope"},                     # bad enum
    {"work_id": "OL1W", "status": "finished", "rating": 9},    # out of range
    {"work_id": "OL1W", "status": "reading", "rating": 4},     # cross-field rule
    {"work_id": "OL1W", "status": "reading", "notes": "x"*501},
])
def test_invalid_payloads_rejected(payload):
    r = httpx.post(f"{BASE}/api/reading-list", json=payload)
    assert r.status_code in (400, 422)

def test_valid_payload():
    r = httpx.post(f"{BASE}/api/reading-list",
                   json={"work_id": "OL1W", "status": "finished", "rating": 5})
    assert r.status_code == 201