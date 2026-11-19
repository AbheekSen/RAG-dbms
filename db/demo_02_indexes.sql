-- DEMO 2: Foreign-key indexes and pgvector similarity index
-- 2a. List all indexes on the project tables (FK indexes are the ix_*_<fk_column> entries).
SELECT tablename, indexname, indexdef FROM pg_indexes
WHERE schemaname='public' AND tablename IN
 ('users','roles','documents','document_chunks','conversations','messages','access_logs')
ORDER BY tablename, indexname;

-- 2b. FK index used for a lookup of one user's documents.
EXPLAIN SELECT * FROM documents WHERE user_id = 1;

-- 2c. pgvector HNSW index used for cosine nearest-neighbour search.
-- (enable_seqscan=off forces the planner to show the index path on small demo tables)
SET enable_seqscan = off;
EXPLAIN SELECT id FROM document_chunks
ORDER BY embedding <=> (SELECT embedding FROM document_chunks LIMIT 1) LIMIT 5;
RESET enable_seqscan;
