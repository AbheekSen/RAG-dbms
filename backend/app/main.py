import re
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from . import rag_core
from .auth import hash_password, verify_password, create_token, current_user, admin_user
from .database import get_db, SessionLocal
from .models import User, Role, Document, Conversation, Message

app = FastAPI(title="RAG Multi-User Document Q&A")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_UPLOAD = 20 * 1024 * 1024


def log(db: Session, user_id, action, detail=None):
    db.execute(text("SELECT fn_log_access(:u, :a, :d)"), {"u": user_id, "a": action, "d": detail})
    db.commit()


def user_out(u: User):
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role.name,
            "created_at": u.created_at.isoformat()}


def doc_out(d: Document):
    return {"id": d.id, "filename": d.filename, "file_type": d.file_type, "status": d.status,
            "error": d.error, "chunk_count": d.chunk_count, "created_at": d.created_at.isoformat()}


# ---------- auth ----------
class RegisterIn(BaseModel):
    name: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


@app.post("/api/auth/register", status_code=201)
def register(p: RegisterIn, db: Session = Depends(get_db)):
    name, email = p.name.strip(), p.email.strip().lower()
    if not name or not EMAIL_RE.match(email):
        raise HTTPException(422, "Valid name and email are required")
    if len(p.password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    role = db.scalar(select(Role).where(Role.name == "user"))
    user = User(name=name, email=email, password_hash=hash_password(p.password), role_id=role.id)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered")
    user = db.get(User, user.id)
    log(db, user.id, "register", email)
    return {"token": create_token(user), "user": user_out(user)}


@app.post("/api/auth/login")
def login(p: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == p.email.strip().lower()))
    if not user or not verify_password(p.password, user.password_hash):
        log(db, user.id if user else None, "login_failed", p.email.strip().lower())
        raise HTTPException(401, "Invalid email or password")
    log(db, user.id, "login")
    return {"token": create_token(user), "user": user_out(user)}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return user_out(user)


# ---------- documents ----------
def _process(doc_id: int, data: bytes):
    with SessionLocal() as db:
        rag_core.index_document(db, doc_id, data)


@app.get("/api/documents")
def list_documents(user: User = Depends(current_user), db: Session = Depends(get_db)):
    docs = db.scalars(select(Document).where(Document.user_id == user.id).order_by(Document.id.desc())).all()
    return [doc_out(d) for d in docs]


@app.post("/api/documents", status_code=202)
async def upload_documents(bg: BackgroundTasks, files: list[UploadFile] = File(...),
                           user: User = Depends(current_user), db: Session = Depends(get_db)):
    created = []
    for f in files:
        ext = (f.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in ("pdf", "txt"):
            raise HTTPException(400, f"{f.filename}: only PDF and TXT files are supported")
        data = await f.read()
        if not data or len(data) > MAX_UPLOAD:
            raise HTTPException(400, f"{f.filename}: file is empty or larger than 20 MB")
        doc = Document(user_id=user.id, filename=f.filename, file_type=ext, status="processing")
        db.add(doc)
        db.commit()
        log(db, user.id, "upload_document", f.filename)
        bg.add_task(_process, doc.id, data)  # each document is processed independently
        created.append(doc_out(doc))
    return created


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None or doc.user_id != user.id:  # users can only touch their own documents
        raise HTTPException(404, "Document not found")
    ok = db.execute(text("SELECT fn_delete_document(:d, :u)"), {"d": doc_id, "u": user.id}).scalar()
    db.commit()
    if not ok:
        raise HTTPException(404, "Document not found")
    return {"ok": True}


# ---------- chat / conversations ----------
class ChatIn(BaseModel):
    query: str
    conversation_id: int | None = None


@app.get("/api/conversations")
def list_conversations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Conversation).where(Conversation.user_id == user.id)
                      .order_by(Conversation.id.desc())).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()} for c in rows]


@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    conv = db.get(Conversation, conv_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    return {"id": conv.id, "title": conv.title,
            "messages": [{"id": m.id, "role": m.role, "content": m.content, "sources": m.sources or [],
                          "created_at": m.created_at.isoformat()} for m in conv.messages]}


@app.post("/api/chat")
def chat(p: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = p.query.strip()
    if not query:
        raise HTTPException(400, "Query cannot be empty")
    if p.conversation_id is not None:
        conv = db.get(Conversation, p.conversation_id)
        if conv is None or conv.user_id != user.id:
            raise HTTPException(404, "Conversation not found")
    else:
        conv = Conversation(user_id=user.id, title=query[:60])
        db.add(conv)
        db.flush()
    try:
        text_out, sources = rag_core.answer(db, user.id, query)
    except Exception:
        db.rollback()
        raise HTTPException(502, "The language model or embedding service is unavailable. Check that Ollama is running.")
    db.add(Message(conversation_id=conv.id, role="user", content=query))
    db.add(Message(conversation_id=conv.id, role="assistant", content=text_out, sources=sources))
    db.commit()
    log(db, user.id, "chat", f"conversation {conv.id}")
    return {"conversation_id": conv.id, "title": conv.title, "answer": text_out, "sources": sources}


# ---------- admin ----------
@app.get("/api/admin/stats")
def admin_stats(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    return dict(db.execute(text("SELECT * FROM fn_admin_stats()")).mappings().one())


@app.get("/api/admin/users")
def admin_users(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    doc_counts = dict(db.execute(select(Document.user_id, func.count()).group_by(Document.user_id)).all())
    conv_counts = dict(db.execute(select(Conversation.user_id, func.count()).group_by(Conversation.user_id)).all())
    return [{**user_out(u), "documents": doc_counts.get(u.id, 0), "conversations": conv_counts.get(u.id, 0)}
            for u in db.scalars(select(User).order_by(User.id)).all()]


@app.get("/api/admin/documents")
def admin_documents(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Document, User.email).join(User, User.id == Document.user_id)
                      .order_by(Document.id.desc())).all()
    return [{**doc_out(d), "owner_email": email} for d, email in rows]
