-- DEMO 3: Stored functions for document / access management
-- 3a. Statistics function
SELECT * FROM fn_admin_stats();

-- 3b. Ownership-checked delete: a different user is refused, the owner succeeds.
INSERT INTO users (name, email, password_hash, role_id)
SELECT 'Other', 'other@example.com', 'x', (SELECT id FROM roles WHERE name='user')
ON CONFLICT (email) DO NOTHING;

INSERT INTO documents (user_id, filename, file_type, status)
SELECT id, 'function_demo.txt', 'txt', 'indexed' FROM users WHERE email='sqldemo@example.com';

SELECT fn_delete_document(
  (SELECT max(id) FROM documents WHERE filename='function_demo.txt'),
  (SELECT id FROM users WHERE email='other@example.com')) AS other_user_can_delete;   -- false

SELECT fn_delete_document(
  (SELECT max(id) FROM documents WHERE filename='function_demo.txt'),
  (SELECT id FROM users WHERE email='sqldemo@example.com')) AS owner_can_delete;      -- true

-- 3c. Both attempts were recorded in access_logs by the function
SELECT user_id, action, detail, created_at FROM access_logs ORDER BY id DESC LIMIT 5;
