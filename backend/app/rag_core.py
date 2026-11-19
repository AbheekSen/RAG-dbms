"""RAG logic: extraction (with page numbers), chunking, embedding, retrieval, generation."""
import io
import ollama
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import config
from .models import Document, DocumentChunk

FALLBACK = "I could not find that information in your documents."

SYSTEM_PROMPT = f"""You are a document assistant.
Answer only using the supplied context. Cite sources like [1], [2] using the numbers given.
If the answer is not in the context, reply exactly:
"{FALLBACK}"
"""

_client = ollama.Client(host=config.OLLAMA_HOST)


def extract_pages(data: bytes, file_type: str):
    """Returns a list of (page_number, text). TXT is treated as a single page."""
    if file_type == "pdf":
        reader = PdfReader(io.BytesIO(data))
        pages = [(i + 1, (p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    else:
        pages = [(1, data.decode("utf-8", errors="ignore"))]
    pages = [(n, t) for n, t in pages if t.strip()]
    if not pages:
        raise ValueError("No extractable text found in document.")
    return pages


def chunk_text(text, size=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP):
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def build_chunks(pages):
    """[(page_number, chunk_text)] with overlap, page numbers preserved."""
    return [(n, c) for n, t in pages for c in chunk_text(t)]


def embed_text(text: str, is_query: bool = False):
    prefix = "search_query: " if is_query else "search_document: "
    return _client.embeddings(model=config.EMBED_MODEL, prompt=prefix + text)["embedding"]


def llm_generate(prompt: str) -> str:
    resp = _client.chat(model=config.CHAT_MODEL, messages=[{"role": "user", "content": prompt}])
    return resp["message"]["content"]


def index_document(db: Session, doc_id: int, data: bytes):
    """Extract -> chunk -> embed -> insert chunks + mark indexed, in ONE transaction.
    Any failure rolls back every chunk; the document is then marked 'failed'."""
    doc = db.get(Document, doc_id)
    try:
        pages = extract_pages(data, doc.file_type)
        rows = build_chunks(pages)
        embeddings = [embed_text(c) for _, c in rows]  # network calls before any insert
        for i, ((page, content), emb) in enumerate(zip(rows, embeddings)):
            db.add(DocumentChunk(document_id=doc.id, user_id=doc.user_id, chunk_index=i,
                                 page_number=page, content=content, embedding=emb))
        doc.chunk_count = len(rows)
        doc.status = "indexed"
        doc.error = None
        db.commit()
    except Exception as e:
        db.rollback()
        doc = db.get(Document, doc_id)
        doc.status = "failed"
        doc.error = str(e)[:500]
        doc.chunk_count = 0
        db.commit()


def retrieve(db: Session, user_id: int, query: str, k: int = config.TOP_K):
    """Cosine-similarity search over the user's own chunks only."""
    q = embed_text(query, is_query=True)
    dist = DocumentChunk.embedding.cosine_distance(q)
    stmt = (select(DocumentChunk, Document.filename, dist.label("distance"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.user_id == user_id, Document.status == "indexed")
            .order_by(dist).limit(k))
    return [(c, fn, d) for c, fn, d in db.execute(stmt).all() if d <= config.MAX_DISTANCE]


def answer(db: Session, user_id: int, query: str):
    """Returns (answer_text, sources)."""
    hits = retrieve(db, user_id, query)
    if not hits:
        return FALLBACK, []
    context = "\n\n".join(f"[{i}] ({fn}, page {c.page_number})\n{c.content}" for i, (c, fn, _) in enumerate(hits, 1))
    text = llm_generate(f"{SYSTEM_PROMPT}\nContext:\n{context}\n\nQuestion: {query}\nAnswer:")
    if FALLBACK.lower() in text.lower():
        return FALLBACK, []
    sources = [{"document_id": c.document_id, "filename": fn, "page": c.page_number,
                "chunk_index": c.chunk_index, "snippet": c.content[:300],
                "score": round(1 - float(d), 3)} for c, fn, d in hits]
    return text, sources
