"""Console-less launcher. Double-click this (it opens with pythonw, no terminal)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import main  # noqa: E402

raise SystemExit(main())
