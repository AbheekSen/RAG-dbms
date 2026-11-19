import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://rag:rag@localhost:5433/ragdb")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2:3b")
EMBED_DIM = 768
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
TOP_K = 4
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "0.75"))  # cosine distance cut-off
