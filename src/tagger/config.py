import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "watch-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_KEY = "tmdb_read_access_token"


def load_api_token():
    if not CONFIG_FILE.exists():
        return None
    try:
        payload = json.loads(CONFIG_FILE.read_text())
    except json.JSONDecodeError:
        return None
    return payload.get(TOKEN_KEY)


def save_api_token(token: str):
    # persist api token for future runs
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({TOKEN_KEY: token}))
