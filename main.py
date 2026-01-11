import sys
from pathlib import Path

# Add 'src' to sys.path to find the 'tagger' package
sys.path.append(str(Path(__file__).parent / "src"))

from tagger.cli import main


if __name__ == "__main__":
    main()
