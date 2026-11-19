-- DEMO 4: Cosine-similarity retrieval over embeddings, restricted to one user's chunks
-- Uses chunk 7 of the demo document as the "query" vector, so it must come back as the closest hit (distance 0).
SELECT c.id, d.filename, c.page_number, left(c.content, 30) AS content,
       c.embedding <=> q.embedding AS cosine_distance,
       1 - (c.embedding <=> q.embedding) AS cosine_similarity
FROM document_chunks c
JOIN documents d ON d.id = c.document_id,
     (SELECT embedding FROM document_chunks WHERE content='demo chunk 7' LIMIT 1) q
WHERE c.user_id = (SELECT id FROM users WHERE email='sqldemo@example.com')
ORDER BY c.embedding <=> q.embedding
LIMIT 5;

-- Same search through the stored function
SELECT chunk_id, filename, page_number, content, distance
FROM fn_search_chunks(
  (SELECT id FROM users WHERE email='sqldemo@example.com'),
  (SELECT embedding FROM document_chunks WHERE content='demo chunk 7' LIMIT 1), 5);

-- Isolation: another user gets nothing
SELECT count(*) AS rows_for_other_user FROM fn_search_chunks(
  (SELECT id FROM users WHERE email='sqldemo@example.com') + 999,
  (SELECT embedding FROM document_chunks LIMIT 1), 5);
