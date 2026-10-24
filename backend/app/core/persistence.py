"""
PRAMAAN-AI lightweight durable storage.

Atomic JSON / JSONL helpers so applications, review runs and the hash-chained audit
ledger survive restarts without adding a database dependency. Persistence is OFF
unless a data directory is supplied (tests stay hermetic); the app enables it via the
PRAMAAN_DATA_DIR environment variable. PostgreSQL remains the documented production target.
"""
import json
import os
import tempfile
import threading
from typing import Any, Iterator, Optional

_write_lock = threading.Lock()


def ensure_dir(data_dir: Optional[str]) -> Optional[str]:
    if not data_dir:
        return None
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def write_json_atomic(path: str, payload: Any) -> None:
    """Write via temp file + rename so a crash never leaves a half-written file."""
    directory = os.path.dirname(path) or "."
    with _write_lock:
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise


def read_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default


def append_jsonl(path: str, record: dict) -> None:
    with _write_lock:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


def read_jsonl(path: str) -> Iterator[dict]:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue  # skip a torn trailing line rather than fail startup
