from __future__ import annotations

import os
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
VENDOR_ROOT = SKILL_ROOT / "vendor"
REPO_ROOT = Path(__file__).resolve().parents[3]
REPO_SRC = REPO_ROOT / "src"
STATE_ROOT = Path.home() / ".codex" / "memories" / "prune-mem-skill"
DEFAULT_WORKSPACE = STATE_ROOT / "workspace"
DEFAULT_CONFIG = STATE_ROOT / "config.local.toml"

if (VENDOR_ROOT / "prune_mem").exists():
    sys.path.insert(0, str(VENDOR_ROOT))
elif str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if DEFAULT_CONFIG.exists():
    os.environ.setdefault("PRUNE_MEM_CONFIG", str(DEFAULT_CONFIG))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from prune_mem.cli import main  # noqa: E402


if __name__ == "__main__":
    sys.argv = ["prune-mem", "--root", str(DEFAULT_WORKSPACE), "prune", "--emit"]
    raise SystemExit(main())
