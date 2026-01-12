import sys
from pathlib import Path

# add local src so the cli is runnable without install
sys.path.append(str(Path(__file__).parent / "src"))

from tagger.entry import app


if __name__ == "__main__":
    app()
