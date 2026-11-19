-- Stored functions for document / access management (idempotent)

CREATE OR REPLACE FUNCTION fn_log_access(p_user_id INT, p_action TEXT, p_detail TEXT DEFAULT NULL)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO access_logs (user_id, action, detail) VALUES (p_user_id, p_action, p_detail);
END;
$$;

-- Deletes a document (chunks cascade) only if the caller owns it or is an admin.
-- Returns TRUE if deleted, FALSE if not found / not permitted. Always writes an access log.
CREATE OR REPLACE FUNCTION fn_delete_document(p_doc_id INT, p_user_id INT)
RETURNS BOOLEAN LANGUAGE plpgsql AS $$
DECLARE
    v_owner INT;
    v_is_admin BOOLEAN;
BEGIN
    SELECT user_id INTO v_owner FROM documents WHERE id = p_doc_id;
    IF v_owner IS NULL THEN
        PERFORM fn_log_access(p_user_id, 'delete_document_failed', 'document ' || p_doc_id || ' not found');
        RETURN FALSE;
    END IF;
    SELECT (r.name = 'admin') INTO v_is_admin
      FROM users u JOIN roles r ON r.id = u.role_id WHERE u.id = p_user_id;
    IF v_owner <> p_user_id AND COALESCE(v_is_admin, FALSE) = FALSE THEN
        PERFORM fn_log_access(p_user_id, 'delete_document_denied', 'document ' || p_doc_id);
        RETURN FALSE;
    END IF;
    DELETE FROM documents WHERE id = p_doc_id;
    PERFORM fn_log_access(p_user_id, 'delete_document', 'document ' || p_doc_id);
    RETURN TRUE;
END;
$$;

-- Basic platform statistics for the admin dashboard.
CREATE OR REPLACE FUNCTION fn_admin_stats()
RETURNS TABLE (users BIGINT, documents BIGINT, chunks BIGINT, conversations BIGINT, messages BIGINT)
LANGUAGE sql STABLE AS $$
    SELECT (SELECT count(*) FROM users), (SELECT count(*) FROM documents),
           (SELECT count(*) FROM document_chunks), (SELECT count(*) FROM conversations),
           (SELECT count(*) FROM messages);
$$;

-- Cosine-similarity retrieval restricted to one user's chunks.
CREATE OR REPLACE FUNCTION fn_search_chunks(p_user_id INT, p_query vector, p_k INT DEFAULT 4)
RETURNS TABLE (chunk_id INT, document_id INT, filename TEXT, page_number INT, content TEXT, distance DOUBLE PRECISION)
LANGUAGE sql STABLE AS $$
    SELECT c.id, c.document_id, d.filename::text, c.page_number, c.content,
           (c.embedding <=> p_query)::double precision
    FROM document_chunks c JOIN documents d ON d.id = c.document_id
    WHERE c.user_id = p_user_id
    ORDER BY c.embedding <=> p_query
    LIMIT p_k;
$$;
