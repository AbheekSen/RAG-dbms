-- Inserts a demo user, a demo document and 200 chunks with random 768-d vectors so the other demos have data.
-- Run AFTER init_db.py. Safe to re-run.
INSERT INTO users (name, email, password_hash, role_id)
SELECT 'SQL Demo', 'sqldemo@example.com', 'not-a-real-hash', (SELECT id FROM roles WHERE name='user')
ON CONFLICT (email) DO NOTHING;

INSERT INTO documents (user_id, filename, file_type, status, chunk_count)
SELECT id, 'sql_demo.txt', 'txt', 'indexed', 200 FROM users WHERE email='sqldemo@example.com'
AND NOT EXISTS (SELECT 1 FROM documents WHERE filename='sql_demo.txt');

INSERT INTO document_chunks (document_id, user_id, chunk_index, page_number, content, embedding)
SELECT d.id, d.user_id, g, (g / 50) + 1, 'demo chunk ' || g,
       (SELECT array_agg(random())::vector FROM generate_series(1,768) WHERE g > 0)
FROM documents d, generate_series(0,199) g
WHERE d.filename='sql_demo.txt' AND NOT EXISTS (SELECT 1 FROM document_chunks WHERE document_id=d.id);

SELECT count(*) AS demo_chunks FROM document_chunks c JOIN documents d ON d.id=c.document_id WHERE d.filename='sql_demo.txt';
