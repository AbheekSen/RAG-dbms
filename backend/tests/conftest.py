import os, re, hashlib, math
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://rag:rag@localhost:5433/ragdb_test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, create_engine
from app import config, rag_core


def _admin_engine():
    url = config.DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    return create_engine(url, isolation_level="AUTOCOMMIT")


def fake_embed(t: str, is_query: bool = False):
    """Deterministic bag-of-words embedding (no Ollama needed): same words -> similar vectors."""
    v = [0.0] * config.EMBED_DIM
    for w in re.findall(r"[a-z]+", t.lower()):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % config.EMBED_DIM] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


@pytest.fixture(scope="session", autouse=True)
def _db():
    name = config.DATABASE_URL.rsplit("/", 1)[1]
    with _admin_engine().connect() as c:
        c.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))
        c.execute(text(f"CREATE DATABASE {name}"))
    from init_db import init_db
    init_db()
    yield


@pytest.fixture(autouse=True)
def _fake_ollama(monkeypatch):
    monkeypatch.setattr(rag_core, "embed_text", fake_embed)
    monkeypatch.setattr(config, "MAX_DISTANCE", 0.95)  # fake bag-of-words vectors are less similar than real ones
    monkeypatch.setattr(rag_core, "llm_generate", lambda prompt: "According to the documents: " + prompt.split("Context:\n")[1][:80])


@pytest.fixture(autouse=True)
def _clean():
    from app.database import engine
    with engine.begin() as c:
        c.execute(text("TRUNCATE access_logs, messages, conversations, document_chunks, documents, users RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture()
def client():
    from app.main import app
    return TestClient(app)


def _signup(client, email, name="Test"):
    r = client.post("/api/auth/register", json={"name": name, "email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture()
def alice(client):
    return _signup(client, "alice@example.com", "Alice")


@pytest.fixture()
def bob(client):
    return _signup(client, "bob@example.com", "Bob")


@pytest.fixture()
def admin(client):
    from seed_admin import seed_admin
    seed_admin("admin@example.com", "Admin@12345")
    r = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "Admin@12345"})
    return {"Authorization": "Bearer " + r.json()["token"]}
