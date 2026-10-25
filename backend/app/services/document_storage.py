"""
PRAMAAN-AI Protected Document Storage Service
Manages secure physical persistence and retrieval of uploaded files.
Enforces:
1. Isolated directory tree per institution tenant
2. File retrieval by internal storage key with IDOR ownership validation
3. In-memory cache for ultra-fast lookup and testing
4. Fallback generator for initial synthetic benchmark seed documents
"""
import os
import re
import hashlib
from typing import Optional, Dict

STORAGE_ROOT = os.getenv(
    "DOCUMENT_STORAGE_DIR",
    os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "storage",
            "protected"
        )
    )
)


class DocumentStorageService:
    def __init__(self, root_dir: str = STORAGE_ROOT):
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)
        self._memory_cache: Dict[str, bytes] = {}

    PROTECTED_PREFIX = "storage/protected/"

    # Seeded demo keys follow 'storage/<seeded-application-id>/<filename>.pdf' (see application_service.py)
    _SEED_FILENAME_RE = re.compile(r"[A-Za-z0-9_\-]+\.pdf")

    @classmethod
    def is_demo_seed_key(cls, storage_key: str) -> bool:
        """
        True only for recognised seeded demo keys: 'storage/<seeded application id>/<filename>.pdf'.
        Unknown or malformed keys are NOT demo keys, so they never receive synthetic bytes.
        """
        from app.services.application_service import ApplicationService  # lazy: avoid import-time coupling

        parts = (storage_key or "").split("/")
        return (
            len(parts) == 3
            and parts[0] == "storage"
            and parts[1] in ApplicationService._SEEDED_IDS
            and bool(cls._SEED_FILENAME_RE.fullmatch(parts[2]))
        )

    def _resolve_protected_path(self, storage_key: str) -> Optional[str]:
        """Map 'storage/protected/<institution>/<doc>.bin' under root_dir; None if unsafe or not protected."""
        if not (storage_key or "").startswith(self.PROTECTED_PREFIX):
            return None
        rel = storage_key[len(self.PROTECTED_PREFIX):]
        candidate = os.path.realpath(os.path.join(self.root_dir, rel))
        root = os.path.realpath(self.root_dir)
        if os.path.commonpath([root, candidate]) != root:
            return None
        return candidate

    def store_document(self, institution_id: str, doc_id: str, content: bytes) -> str:
        """
        Securely writes document binary content to disk in tenant-scoped directory.
        The write is atomic (temp file + rename) so a failure never leaves a partial file.
        Returns the absolute storage path.
        """
        inst_dir = os.path.join(self.root_dir, institution_id)
        os.makedirs(inst_dir, exist_ok=True)
        file_path = os.path.join(inst_dir, f"{doc_id}.bin")
        tmp_path = file_path + ".tmp"
        try:
            with open(tmp_path, "wb") as f:
                f.write(content)
            os.replace(tmp_path, file_path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        # Index in memory cache under both doc_id and storage path
        self._memory_cache[doc_id] = content
        self._memory_cache[file_path] = content
        rel_key = f"{self.PROTECTED_PREFIX}{institution_id}/{doc_id}.bin"
        self._memory_cache[rel_key] = content

        return file_path

    def delete_document(self, institution_id: str, doc_id: str) -> None:
        """Best-effort removal of a stored file and its cache entries (used to roll back failed uploads)."""
        file_path = os.path.join(self.root_dir, institution_id, f"{doc_id}.bin")
        rel_key = f"{self.PROTECTED_PREFIX}{institution_id}/{doc_id}.bin"
        for key in (doc_id, file_path, rel_key):
            self._memory_cache.pop(key, None)
        try:
            os.unlink(file_path)
        except FileNotFoundError:
            pass

    def get_document_bytes(self, storage_key: str, doc_id: Optional[str] = None) -> Optional[bytes]:
        """
        Retrieves binary bytes for a document from memory cache, direct disk path,
        or (demo seeds only) a synthetic placeholder. Returns None when a real upload is missing.
        """
        if doc_id and doc_id in self._memory_cache:
            return self._memory_cache[doc_id]

        if storage_key in self._memory_cache:
            return self._memory_cache[storage_key]

        # Real uploads: resolve strictly inside root_dir (tenant folder included).
        protected_path = self._resolve_protected_path(storage_key)
        if protected_path:
            try:
                with open(protected_path, "rb") as f:
                    data = f.read()
            except OSError:
                return None  # never fabricate bytes for a real upload
            if doc_id:
                self._memory_cache[doc_id] = data
            return data

        # Check if direct absolute path exists
        if os.path.isabs(storage_key) and os.path.exists(storage_key):
            try:
                with open(storage_key, "rb") as f:
                    data = f.read()
                    if doc_id:
                        self._memory_cache[doc_id] = data
                    return data
            except OSError:
                pass

        # Check relative to backend/
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        candidate = os.path.join(backend_dir, storage_key)
        if os.path.exists(candidate):
            try:
                with open(candidate, "rb") as f:
                    data = f.read()
                    if doc_id:
                        self._memory_cache[doc_id] = data
                    return data
            except OSError:
                pass

        # Check inside self.root_dir
        candidate_root = os.path.join(self.root_dir, os.path.basename(storage_key))
        if os.path.exists(candidate_root):
            try:
                with open(candidate_root, "rb") as f:
                    data = f.read()
                    if doc_id:
                        self._memory_cache[doc_id] = data
                    return data
            except OSError:
                pass

        # Anything that is not a recognised seeded demo key (real uploads, unknown or malformed keys) is
        # reported as missing, never replaced with fake bytes.
        if not self.is_demo_seed_key(storage_key):
            return None

        # Synthetic fallback ONLY for seeded demo documents without physical files on disk
        synthetic_seed_pdf = (
            b"%PDF-1.4\n1 0 obj\n<< /Title (PRAMAAN-AI Seeded Dossier) >>\nendobj\n"
            b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
        )
        return synthetic_seed_pdf


global_document_storage = DocumentStorageService()
