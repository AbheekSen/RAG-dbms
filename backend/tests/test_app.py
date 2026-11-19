import os
import pytest
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from app import rag_core
from app.database import engine, SessionLocal
from app.models import Document, DocumentChunk, User

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "sample_docs")
LEAVE = ("leave.txt", b"Annual leave: employees receive 24 days of paid annual leave each year. " * 12, "text/plain")
DB_NOTES = ("db.txt", b"Cosine similarity measures the angle between embedding vectors in pgvector. " * 12, "text/plain")


def upload(client, headers, *files):
    return client.post("/api/documents", headers=headers, files=[("files", f) for f in files])


# ---- authentication and roles ----
def test_register_login_me(client):
    r = client.post("/api/auth/register", json={"name": "A", "email": "a@x.com", "password": "password123"})
    assert r.status_code == 201 and r.json()["user"]["role"] == "user"
    assert client.post("/api/auth/register", json={"name": "A", "email": "a@x.com", "password": "password123"}).status_code == 409
    assert client.post("/api/auth/register", json={"name": "A", "email": "bad", "password": "password123"}).status_code == 422
    assert client.post("/api/auth/register", json={"name": "A", "email": "b@x.com", "password": "short"}).status_code == 422
    assert client.post("/api/auth/login", json={"email": "a@x.com", "password": "wrong"}).status_code == 401
    tok = client.post("/api/auth/login", json={"email": "a@x.com", "password": "password123"}).json()["token"]
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["email"] == "a@x.com"
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_password_is_hashed(client, alice):
    with Session(engine) as db:
        u = db.scalar(select(User).where(User.email == "alice@example.com"))
        assert u.password_hash != "password123" and u.password_hash.startswith("$2")


def test_admin_access(client, alice, admin):
    assert client.get("/api/admin/stats", headers=alice).status_code == 403
    assert client.get("/api/admin/users", headers=alice).status_code == 403
    assert client.get("/api/admin/documents", headers=alice).status_code == 403
    assert client.get("/api/admin/stats").status_code == 401
    s = client.get("/api/admin/stats", headers=admin).json()
    assert s["users"] == 2
    users = client.get("/api/admin/users", headers=admin).json()
    assert {u["email"] for u in users} == {"alice@example.com", "admin@example.com"}
    upload(client, alice, LEAVE)
    docs = client.get("/api/admin/documents", headers=admin).json()
    assert docs[0]["owner_email"] == "alice@example.com"


# ---- documents ----
def test_upload_list_delete_multiple_docs(client, alice):
    r = upload(client, alice, LEAVE, DB_NOTES)
    assert r.status_code == 202 and len(r.json()) == 2
    docs = client.get("/api/documents", headers=alice).json()
    assert len(docs) == 2 and all(d["status"] == "indexed" and d["chunk_count"] > 0 for d in docs)
    upload(client, alice, LEAVE)  # same name again must not overwrite
    assert len(client.get("/api/documents", headers=alice).json()) == 3
    doc_id = docs[0]["id"]
    assert client.delete(f"/api/documents/{doc_id}", headers=alice).status_code == 200
    assert len(client.get("/api/documents", headers=alice).json()) == 2
    with Session(engine) as db:
        assert db.scalar(text("SELECT count(*) FROM document_chunks WHERE document_id=:d"), {"d": doc_id}) == 0
    assert client.delete(f"/api/documents/{doc_id}", headers=alice).status_code == 404


def test_rejects_bad_file_type(client, alice):
    assert upload(client, alice, ("x.exe", b"abc", "application/octet-stream")).status_code == 400
    assert client.post("/api/documents", files=[("files", LEAVE)]).status_code == 401


# ---- chunking and embedding storage ----
def test_chunking_overlap_and_pdf_pages():
    chunks = rag_core.chunk_text("a" * 1000, size=500, overlap=100)
    assert len(chunks) == 3 and chunks[0][-100:] == chunks[1][:100]
    with open(os.path.join(SAMPLES, "database_systems_notes.pdf"), "rb") as f:
        pages = rag_core.extract_pages(f.read(), "pdf")
    assert [n for n, _ in pages] == [1, 2, 3]


def test_embeddings_stored_in_pgvector(client, alice):
    with open(os.path.join(SAMPLES, "database_systems_notes.pdf"), "rb") as f:
        upload(client, alice, ("notes.pdf", f.read(), "application/pdf"))
    with Session(engine) as db:
        chunks = db.scalars(select(DocumentChunk)).all()
        assert chunks and {c.page_number for c in chunks} == {1, 2, 3}
        assert all(len(c.embedding) == 768 for c in chunks)


# ---- vector retrieval and citations ----
def test_retrieval_and_citations(client, alice):
    with open(os.path.join(SAMPLES, "database_systems_notes.pdf"), "rb") as f:
        upload(client, alice, ("notes.pdf", f.read(), "application/pdf"))
    r = client.post("/api/chat", headers=alice, json={"query": "What is cosine similarity in pgvector?"})
    assert r.status_code == 200
    src = r.json()["sources"]
    assert src and src[0]["filename"] == "notes.pdf" and src[0]["page"] == 3
    r2 = client.post("/api/chat", headers=alice, json={"query": "How do transactions rollback?"})
    assert r2.json()["sources"][0]["page"] == 1


def test_fallback_when_no_information(client, alice):
    r = client.post("/api/chat", headers=alice, json={"query": "anything at all"})  # no documents yet
    assert r.json()["answer"] == rag_core.FALLBACK and r.json()["sources"] == []
    upload(client, alice, LEAVE)
    r = client.post("/api/chat", headers=alice, json={"query": "quantum chromodynamics gluon"})
    assert r.json()["answer"] == rag_core.FALLBACK


# ---- conversation persistence ----
def test_conversation_persistence(client, alice):
    upload(client, alice, LEAVE)
    r = client.post("/api/chat", headers=alice, json={"query": "How many days of annual leave?"}).json()
    cid = r["conversation_id"]
    client.post("/api/chat", headers=alice, json={"query": "And paid leave per year?", "conversation_id": cid})
    convs = client.get("/api/conversations", headers=alice).json()
    assert len(convs) == 1 and convs[0]["id"] == cid
    msgs = client.get(f"/api/conversations/{cid}", headers=alice).json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert msgs[1]["sources"][0]["filename"] == "leave.txt"  # citations persisted
    with Session(engine) as db:
        assert db.scalar(text("SELECT count(*) FROM messages WHERE conversation_id=:c"), {"c": cid}) == 4


# ---- user data isolation ----
def test_user_isolation(client, alice, bob):
    upload(client, alice, LEAVE)
    doc_id = client.get("/api/documents", headers=alice).json()[0]["id"]
    assert client.get("/api/documents", headers=bob).json() == []
    assert client.delete(f"/api/documents/{doc_id}", headers=bob).status_code == 404
    assert len(client.get("/api/documents", headers=alice).json()) == 1
    r = client.post("/api/chat", headers=bob, json={"query": "How many days of annual leave?"}).json()
    assert r["answer"] == rag_core.FALLBACK and r["sources"] == []  # bob cannot retrieve alice's chunks
    cid = client.post("/api/chat", headers=alice, json={"query": "annual leave days"}).json()["conversation_id"]
    assert client.get(f"/api/conversations/{cid}", headers=bob).status_code == 404
    assert cid not in [c["id"] for c in client.get("/api/conversations", headers=bob).json()]
    assert client.post("/api/chat", headers=bob, json={"query": "hi", "conversation_id": cid}).status_code == 404


# ---- transaction rollback ----
def test_transaction_rollback_on_failure(client, alice, monkeypatch):
    calls = {"n": 0}
    real = rag_core.embed_text

    def flaky(t, is_query=False):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("embedding failure")
        return real(t, is_query)

    monkeypatch.setattr(rag_core, "embed_text", flaky)
    upload(client, alice, ("big.txt", b"word " * 600, "text/plain"))
    d = client.get("/api/documents", headers=alice).json()[0]
    assert d["status"] == "failed" and d["chunk_count"] == 0
    with Session(engine) as db:
        assert db.scalar(text("SELECT count(*) FROM document_chunks")) == 0


def test_rollback_on_chunk_insert_error(client, alice):
    """Failure at INSERT time (bad vector dimension) rolls back the earlier chunks of the same document."""
    with Session(engine) as db:
        uid = db.scalar(select(User.id))
        doc = Document(user_id=uid, filename="t.txt", file_type="txt")
        db.add(doc); db.commit()
        db.add(DocumentChunk(document_id=doc.id, user_id=uid, chunk_index=0, page_number=1, content="ok", embedding=[0.1] * 768))
        db.add(DocumentChunk(document_id=doc.id, user_id=uid, chunk_index=1, page_number=1, content="bad", embedding=[0.1] * 5))
        with pytest.raises(Exception):
            db.commit()
        db.rollback()
        assert db.scalar(text("SELECT count(*) FROM document_chunks")) == 0


# ---- stored functions ----
def test_stored_function_delete_and_log(client, alice, bob):
    upload(client, alice, LEAVE)
    doc_id = client.get("/api/documents", headers=alice).json()[0]["id"]
    with Session(engine) as db:
        bob_id = db.scalar(select(User.id).where(User.email == "bob@example.com"))
        alice_id = db.scalar(select(User.id).where(User.email == "alice@example.com"))
        assert db.execute(text("SELECT fn_delete_document(:d,:u)"), {"d": doc_id, "u": bob_id}).scalar() is False
        assert db.execute(text("SELECT fn_delete_document(:d,:u)"), {"d": doc_id, "u": alice_id}).scalar() is True
        db.commit()
        acts = [r[0] for r in db.execute(text("SELECT action FROM access_logs ORDER BY id"))]
        assert "delete_document_denied" in acts and "delete_document" in acts


def test_fn_search_chunks_cosine(client, alice):
    upload(client, alice, LEAVE, DB_NOTES)
    q = str(rag_core.embed_text("cosine similarity vectors", True))
    with Session(engine) as db:
        uid = db.scalar(select(User.id))
        rows = db.execute(text("SELECT filename, distance FROM fn_search_chunks(:u, CAST(:q AS vector), 3)"),
                          {"u": uid, "q": q}).all()
        assert rows[0][0] == "db.txt" and rows[0][1] <= rows[-1][1]
