import os
from pathlib import Path

# Caminho base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Carregar arquivo .env manualmente se existir para evitar dependência externa
env_path = BASE_DIR / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

# Diretórios de dados
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DATA_DIR = DATA_DIR / "outputs"

# Configurações do GitHub
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_TOKENS_RAW = os.getenv("GITHUB_TOKENS", "")
if GITHUB_TOKENS_RAW:
    GITHUB_TOKENS = [t.strip() for t in GITHUB_TOKENS_RAW.split(",") if t.strip()]
else:
    GITHUB_TOKENS = [GITHUB_TOKEN] if GITHUB_TOKEN else []
DEFAULT_REPO = "encode/fastapi"

def init_directories():
    """Garante que todas as pastas de dados necessárias existam no disco."""
    for path in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DATA_DIR]:
        path.mkdir(parents=True, exist_ok=True)

# Inicializar pastas na importação do módulo
init_directories()
