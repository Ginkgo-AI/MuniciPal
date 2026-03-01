import asyncio
from municipal.web.app import create_app
from fastapi.testclient import TestClient

app = create_app()
client = TestClient(app)

response = client.post("/api/sessions", json={"session_type": "anonymous"})
session_id = response.json()["session_id"]
print("Testing with session", session_id)

try:
    response = client.post("/api/chat", json={"session_id": session_id, "message": "can you help me get trash service?"})
    print(response.json())
except Exception as e:
    print("Caught Exception:", e)
