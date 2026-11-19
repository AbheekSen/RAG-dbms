# DocuMind - RAG-Based Multi-User Document Q&A Platform

React + Vite + Tailwind frontend, FastAPI backend, PostgreSQL + pgvector, Ollama (`nomic-embed-text`, `llama3.2:3b`).

```
rag_platform/
  docker-compose.yml        PostgreSQL 16 + pgvector
  .env.example              copy to backend\.env
  db/                       functions.sql, indexes.sql, demo_00..04 SQL demos
  docs/                     er_diagram.svg, er_diagram.md
  backend/                  FastAPI app (app/), init_db.py, seed_admin.py, tests/, sample_docs/
  frontend/                 React app
```

## Prerequisites (install once)
1. **Docker Desktop** (running) - https://www.docker.com/products/docker-desktop
2. **Ollama for Windows** - https://ollama.com/download
3. **Python 3.11+** (tick "Add to PATH") and **Node.js 18+**

## Run it (Windows 11, PowerShell, VS Code)
Use **PowerShell Terminal 1** for steps 1-8, **Terminal 2** for FastAPI, **Terminal 3** for React (VS Code: Terminal > New Terminal; the `+` button opens more).

**1. Extract** (Terminal 1)
```powershell
Expand-Archive -Path "$HOME\Downloads\rag_platform.zip" -DestinationPath "$HOME\Documents" -Force
cd "$HOME\Documents\rag_platform"
code .
```

**2. Configure .env** (Terminal 1)
```powershell
Copy-Item .env.example backend\.env
```
Optionally edit `backend\.env` (change `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`).

**3. Start PostgreSQL + pgvector** (Terminal 1; Docker Desktop must be running)
```powershell
docker compose up -d
docker ps        # rag_postgres should be "Up"
```

**4. Ollama + models** (Terminal 1; Ollama normally auto-starts after install - if the first command errors, run `ollama serve` in a separate terminal)
```powershell
ollama pull nomic-embed-text
ollama pull llama3.2:3b
ollama list
```

**5. Backend dependencies** (Terminal 1)
```powershell
cd backend
py -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**6. Initialize the database** (Terminal 1, venv active) - creates the pgvector extension, 7 tables, indexes, stored functions, roles
```powershell
python init_db.py
```

**7. Create the admin account** (Terminal 1, venv active)
```powershell
python seed_admin.py
```
Default login: `admin@example.com` / `Admin@12345` (from `.env`).

**8. Frontend dependencies** (Terminal 3)
```powershell
cd "$HOME\Documents\rag_platform\frontend"
npm install
```

**9. Start FastAPI** (Terminal 2)
```powershell
cd "$HOME\Documents\rag_platform\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

**10. Start React** (Terminal 3)
```powershell
npm run dev
```
Open http://localhost:5173

## Try the app
1. Register a normal user (or sign in as the admin) -> **Documents** -> drag in `backend\sample_docs\database_systems_notes.pdf` and `company_leave_policy.txt`. Wait for the badge to say **Indexed**.
2. **AI Chat** -> ask "What is cosine similarity?" (cites database_systems_notes.pdf, page 3) and "How many days of annual leave do I get?" (cites the TXT file). Ask something unrelated to get the "could not find" fallback.
3. Click a past conversation in the history panel to reopen it.
4. Register a second user: they see none of the first user's documents/chats.
5. Sign in as admin -> **Admin** for stats, users and all documents.

## Demonstrate the advanced database features (Terminal 1, from the project root)
No local `psql` needed - the scripts run inside the Docker container.
```powershell
cd "$HOME\Documents\rag_platform"
Get-Content db\demo_00_seed_demo_data.sql   | docker exec -i rag_postgres psql -U rag -d ragdb
Get-Content db\demo_01_transaction_rollback.sql | docker exec -i rag_postgres psql -U rag -d ragdb
Get-Content db\demo_02_indexes.sql          | docker exec -i rag_postgres psql -U rag -d ragdb
Get-Content db\demo_03_stored_functions.sql | docker exec -i rag_postgres psql -U rag -d ragdb
Get-Content db\demo_04_vector_search.sql    | docker exec -i rag_postgres psql -U rag -d ragdb
```
| Script | Shows |
|---|---|
| demo_01 | Transaction: document + chunk insert, forced error, `ROLLBACK` -> counts back to 0 |
| demo_02 | Foreign-key indexes (`ix_*_user_id`, ...) and the pgvector HNSW cosine index in `EXPLAIN` |
| demo_03 | Stored functions `fn_delete_document` (ownership check + logging), `fn_admin_stats`, `fn_log_access` |
| demo_04 | Cosine-similarity retrieval (`<=>`) with per-user filtering, plus `fn_search_chunks` |

In the app, the same mechanisms run for real: uploads index chunks inside one transaction (rollback on failure), deletion calls `fn_delete_document`, admin stats call `fn_admin_stats`, and chat retrieval uses cosine distance on the HNSW index.

## Automated tests (Terminal 1, venv active, in `backend`)
```powershell
cd backend
pytest -q
```
Tests use a real PostgreSQL/pgvector database (`ragdb_test`, created automatically) and replace Ollama with deterministic stand-ins so they run without models.

## Notes
- Documents are indexed in the background; failed indexing (e.g. Ollama not running) is shown as **Failed** with the reason - delete and re-upload after fixing.
- Retrieval ignores chunks with cosine distance above `MAX_DISTANCE` (default 0.75, set in `.env`); tune it if answers fall back too often or too rarely.
- Stop everything: `Ctrl+C` in Terminals 2 and 3, then `docker compose down` (add `-v` to wipe the data).
