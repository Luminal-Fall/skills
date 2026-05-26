import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock external dependencies before evaluation.py is imported
for mod in ("anthropic", "connections"):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
