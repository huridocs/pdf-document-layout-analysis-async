import os
from pathlib import Path

import configuration


class PdfFile:
    def __init__(self, tenant: str):
        self.tenant = tenant

    def get_path(self, pdf_file_name: str):
        return Path(f"{configuration.DATA_PATH}/{self.tenant}/{pdf_file_name}")

    def save(self, pdf_file_name: str, file: bytes):
        os.makedirs(f"{configuration.DATA_PATH}/{self.tenant}", exist_ok=True)
        self.get_path(pdf_file_name).write_bytes(file)
