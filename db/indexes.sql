-- pgvector similarity index (cosine). FK indexes are created by the SQLAlchemy models (ix_* names).
CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS ix_access_logs_created_at ON access_logs (created_at);
