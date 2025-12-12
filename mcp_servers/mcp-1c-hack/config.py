"""Configuration helpers for the Universal 1C MCP server."""

from __future__ import annotations

import glob
import os
from pathlib import Path

from platformdirs import user_cache_dir


CACHE_DIR: Path = Path(user_cache_dir("universal-1c-mcp", "mcp"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_ONEC_EXE_CACHE: Path | None = None


def discover_onec_executable() -> Path:
    """
    Locate 1C executable (1cv8.exe/1cv8c.exe).

    Search order:
    1) `ONEC_BIN_PATH` env var
    2) `C:\\Program Files\\1cv8\\*\\bin\\(1cv8|1cv8c).exe`
    3) `C:\\Program Files (x86)\\1cv8\\*\\bin\\(1cv8|1cv8c).exe`

    Returns:
        Path to 1C executable.

    Raises:
        FileNotFoundError: If 1C executable cannot be found.
    """

    env_path = (os.getenv("ONEC_BIN_PATH") or "").strip()
    candidates: list[Path] = []

    if env_path:
        candidates.append(Path(env_path))

    default_roots = [
        Path(r"C:\Program Files\1cv8"),
        Path(r"C:\Program Files (x86)\1cv8"),
    ]

    for root in default_roots:
        if not root.exists():
            continue
        candidates.extend(Path(p) for p in glob.glob(str(root / "*" / "bin" / "1cv8.exe")))
        candidates.extend(Path(p) for p in glob.glob(str(root / "*" / "bin" / "1cv8c.exe")))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Не удалось найти 1С (1cv8.exe/1cv8c.exe). "
        "Укажите путь через переменную окружения ONEC_BIN_PATH."
    )


def get_onec_executable() -> Path:
    """Return cached 1C executable path (lazy discovery)."""

    global _ONEC_EXE_CACHE
    if _ONEC_EXE_CACHE is None:
        _ONEC_EXE_CACHE = discover_onec_executable()
    return _ONEC_EXE_CACHE

