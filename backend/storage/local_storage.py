"""
Local File Storage Provider for Clarivens.
Used during local development and testing.
Organizes files by org/project and UUID identifiers to guarantee isolation.
"""
import os
import shutil
import logging
from typing import BinaryIO, Optional

logger = logging.getLogger(__name__)

class LocalStorageProvider:
    def __init__(self, base_dir: str = "backend/uploads"):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, org_id: str, project_id: str, file_name: str) -> str:
        safe_org = str(org_id).replace("..", "").strip("/\\")
        safe_proj = str(project_id).replace("..", "").strip("/\\")
        safe_file = os.path.basename(file_name)
        folder = os.path.join(self.base_dir, safe_org, safe_proj)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, safe_file)

    def save_file(self, file_content: bytes, org_id: str, project_id: str, storage_name: str) -> str:
        target_path = self._get_path(org_id, project_id, storage_name)
        with open(target_path, "wb") as f:
            f.write(file_content)
        return target_path

    def get_file(self, org_id: str, project_id: str, storage_name: str) -> Optional[bytes]:
        target_path = self._get_path(org_id, project_id, storage_name)
        if os.path.exists(target_path):
            with open(target_path, "rb") as f:
                return f.read()
        return None

    def delete_file(self, org_id: str, project_id: str, storage_name: str) -> bool:
        target_path = self._get_path(org_id, project_id, storage_name)
        if os.path.exists(target_path):
            os.remove(target_path)
            return True
        return False
