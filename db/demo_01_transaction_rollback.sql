-- DEMO 1: Atomic document + chunk insertion with ROLLBACK
-- Expected: the 'before' and 'after' counts are identical, proving the rollback undid everything.
SELECT count(*) AS documents_before FROM documents WHERE filename = 'rollback_demo.txt';

BEGIN;
INSERT INTO documents (user_id, filename, file_type, status)
VALUES ((SELECT id FROM users WHERE email='sqldemo@example.com'), 'rollback_demo.txt', 'txt', 'processing');

INSERT INTO document_chunks (document_id, user_id, chunk_index, page_number, content, embedding)
SELECT d.id, d.user_id, 0, 1, 'first chunk', (SELECT array_agg(random())::vector FROM generate_series(1,768))
FROM documents d WHERE d.filename='rollback_demo.txt';

SELECT count(*) AS documents_inside_txn FROM documents WHERE filename = 'rollback_demo.txt';

-- Simulate a failure: wrong vector dimension is rejected, so the whole unit of work must be undone.
-- (psql aborts the transaction on this error; the ROLLBACK below ends it.)
INSERT INTO document_chunks (document_id, user_id, chunk_index, page_number, content, embedding)
SELECT d.id, d.user_id, 1, 1, 'bad chunk', '[1,2,3]'::vector
FROM documents d WHERE d.filename='rollback_demo.txt';
ROLLBACK;

SELECT count(*) AS documents_after FROM documents WHERE filename = 'rollback_demo.txt';
SELECT count(*) AS chunks_after FROM document_chunks WHERE content IN ('first chunk','bad chunk');
