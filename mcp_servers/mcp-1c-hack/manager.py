"""1C metadata dump and index builder."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from config import CACHE_DIR, get_onec_executable
from parser import TYPE_MAP, parse_folder


class OneCManager:
    """Build and cache an index of 1C configuration objects."""

    def __init__(
        self,
        exe_path: Path | None = None,
        timeout_sec: int = 300,
        dump_root: Path | None = None,
    ) -> None:
        self.exe_path: Path | None = Path(exe_path) if exe_path else None
        self.timeout_sec = timeout_sec
        self.dump_root = dump_root or (CACHE_DIR / "dumps")
        self.dump_root.mkdir(parents=True, exist_ok=True)

    def _ensure_exe_path(self) -> Path:
        if self.exe_path is None:
            self.exe_path = get_onec_executable()
        return self.exe_path

    def _cache_path(self, connection_string: str) -> Path:
        cache_key = hashlib.md5(connection_string.encode("utf-8")).hexdigest()
        return CACHE_DIR / f"{cache_key}.json"

    def get_index(
        self,
        connection_string: str,
        username: str = "",
        password: str = "",
        force_update: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Build or load cached configuration index for the given 1C connection.

        Args:
            connection_string: 1C connection string (File=... or IBConnectionString).
            username: 1C designer/configurator username.
            password: 1C designer/configurator password.
            force_update: Force re-dump and rebuild cache.

        Returns:
            List of indexed objects with `name`, `synonym`, `type`, `search_text`, etc.

        Raises:
            RuntimeError: If 1C dump fails or times out.
            FileNotFoundError: If 1C executable cannot be located.
        """

        connection_string = (connection_string or "").strip()
        if not connection_string:
            raise ValueError("connection_string is required")

        cache_file = self._cache_path(connection_string)
        if cache_file.exists() and not force_update:
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        dump_dir = self.dump_root / hashlib.md5(connection_string.encode("utf-8")).hexdigest()
        lock_file = dump_dir.with_suffix(".lock")

        if dump_dir.exists() and self._dump_ready(dump_dir) and not force_update:
            index = parse_folder(dump_dir)
            cache_file.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
            return index

        if lock_file.exists() and not force_update:
            waited = 0
            sleep_step = 5
            while waited < self.timeout_sec:
                time.sleep(sleep_step)
                waited += sleep_step
                if self._dump_ready(dump_dir):
                    index = parse_folder(dump_dir)
                    cache_file.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
                    return index
            raise RuntimeError("Timeout while waiting for another dump process to finish")

        dump_dir.mkdir(parents=True, exist_ok=True)
        lock_file.touch(exist_ok=True)

        cmd = self._build_designer_command(
            connection_string=connection_string,
            username=username,
            password=password,
            dump_dir=dump_dir,
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
            )
        except FileNotFoundError:
            lock_file.unlink(missing_ok=True)
            raise
        except subprocess.TimeoutExpired as exc:
            lock_file.unlink(missing_ok=True)
            raise RuntimeError("1C dump timed out") from exc

        if result.returncode != 0:
            lock_file.unlink(missing_ok=True)
            raise RuntimeError(
                "1C dump failed. "
                f"ExitCode={result.returncode}. STDOUT={result.stdout} STDERR={result.stderr}"
            )

        index = parse_folder(dump_dir)
        lock_file.unlink(missing_ok=True)
        cache_file.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        return index

    def _build_designer_command(
        self,
        connection_string: str,
        username: str,
        password: str,
        dump_dir: Path,
    ) -> list[str]:
        """
        Build 1C DESIGNER command line to dump config to files.

        Examples:
            File="C:\\Base"; -> /F "<path>"
            Srvr="srv";Ref="base"; -> /IBConnectionString "Srvr=srv;Ref=base;"
        """

        exe = str(self._ensure_exe_path())
        conn = connection_string.strip()
        is_file = conn.lower().startswith("file=")

        if is_file:
            path_part = conn.split("=", 1)[1].strip().strip('";').strip()
            return [
                exe,
                "DESIGNER",
                "/F",
                path_part,
                "/N",
                username or "",
                "/P",
                password or "",
                "/DumpConfigToFiles",
                str(dump_dir),
            ]

        cmd_conn_parts: list[str] = []
        for part in conn.strip('"').split(";"):
            p = part.strip()
            if not p:
                continue
            if "=" in p:
                k, v = p.split("=", 1)
                cmd_conn_parts.append(f"{k.strip()}={v.strip().strip('\"')}")
            else:
                cmd_conn_parts.append(p)

        normalized_conn = ";".join(cmd_conn_parts)
        if not normalized_conn.endswith(";"):
            normalized_conn += ";"

        return [
            exe,
            "DESIGNER",
            "/IBConnectionString",
            normalized_conn,
            "/N",
            username or "",
            "/P",
            password or "",
            "/DumpConfigToFiles",
            str(dump_dir),
        ]

    def _dump_ready(self, dump_dir: Path) -> bool:
        """Heuristic check that `DumpConfigToFiles` has completed."""

        if not dump_dir.exists():
            return False

        marker_files = ["ConfigDumpInfo.xml", "Configuration.xml"]
        if any((dump_dir / marker).exists() for marker in marker_files):
            return True

        for folder in TYPE_MAP.keys():
            sub = dump_dir / folder
            if sub.exists() and list(sub.glob("*.xml")):
                return True

        return False

