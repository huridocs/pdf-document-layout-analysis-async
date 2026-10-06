import threading
import time
from pathlib import Path
from typing import Optional

from psycopg_pool import ConnectionPool

import configuration


def _is_old(path: Path, retention_seconds: float) -> bool:
    try:
        return (time.time() - path.stat().st_mtime) > retention_seconds
    except FileNotFoundError:
        return False


def _prune_empty_dir(directory: Path) -> None:
    try:
        directory.rmdir()
    except OSError:
        pass


def _sweep_xml_files(data_path: Path, retention_seconds: float) -> int:
    removed = 0
    for xml_file in data_path.iterdir():
        if xml_file.is_file() and xml_file.suffix == ".xml" and _is_old(xml_file, retention_seconds):
            xml_file.unlink(missing_ok=True)
            removed += 1
    return removed


def _sweep_ocr_output(ocr_output: Path, retention_seconds: float) -> int:
    removed = 0
    for tenant_dir in ocr_output.iterdir():
        if not tenant_dir.is_dir():
            continue
        for ocr_file in tenant_dir.iterdir():
            if ocr_file.is_file() and _is_old(ocr_file, retention_seconds):
                ocr_file.unlink(missing_ok=True)
                removed += 1
        _prune_empty_dir(tenant_dir)
    return removed


def _sweep_uploaded_pdfs(data_path: Path, ocr_output: Path, retention_seconds: float) -> int:
    removed = 0
    for tenant_dir in data_path.iterdir():
        if not tenant_dir.is_dir() or tenant_dir == ocr_output:
            continue
        for pdf_file in tenant_dir.iterdir():
            if pdf_file.is_file() and _is_old(pdf_file, retention_seconds):
                pdf_file.unlink(missing_ok=True)
                removed += 1
        _prune_empty_dir(tenant_dir)
    return removed


def _sweep_paragraphs(connection_pool: ConnectionPool, retention_hours: float) -> int:
    with connection_pool.connection() as connection:
        deleted = connection.execute(
            "DELETE FROM paragraphs WHERE updated_at < NOW() - (%s * interval '1 hour') RETURNING id",
            (retention_hours,),
        )
        connection.commit()
        return len(deleted.fetchall())


def sweep_old_materials(
    retention_hours: float,
    data_path: Optional[Path] = None,
    ocr_output: Optional[Path] = None,
    connection_pool: Optional[ConnectionPool] = None,
) -> int:
    """Deletes materials older than `retention_hours`: XML files flat in DATA_PATH, OCR results,
    uploaded PDFs inside tenant directories, and paragraphs rows. Returns the number removed."""
    if retention_hours <= 0:
        return 0
    retention_seconds = retention_hours * 3600
    data_path = data_path or Path(configuration.DATA_PATH)
    ocr_output = ocr_output or Path(configuration.OCR_OUTPUT)

    configuration.service_logger.info(f"Sweeping materials older than {retention_hours} hours")

    removed = 0
    try:
        removed += _sweep_xml_files(data_path, retention_seconds)
    except Exception:
        configuration.service_logger.exception("Error sweeping old XML files")
    try:
        removed += _sweep_ocr_output(ocr_output, retention_seconds)
    except Exception:
        configuration.service_logger.exception("Error sweeping old OCR results")
    try:
        removed += _sweep_uploaded_pdfs(data_path, ocr_output, retention_seconds)
    except Exception:
        configuration.service_logger.exception("Error sweeping old uploaded PDFs")
    if connection_pool:
        try:
            removed += _sweep_paragraphs(connection_pool, retention_hours)
        except Exception:
            configuration.service_logger.exception("Error sweeping old paragraphs")

    return removed


_sweep_lock = threading.Lock()
_last_sweep = 0.0


def sweep_if_due(
    retention_hours: float,
    min_interval_minutes: float,
    data_path: Optional[Path] = None,
    ocr_output: Optional[Path] = None,
    connection_pool: Optional[ConnectionPool] = None,
) -> None:
    """Throttled sweep: runs `sweep_old_materials` at most once per `min_interval_minutes`."""
    global _last_sweep
    if retention_hours <= 0:
        return
    with _sweep_lock:
        if (time.time() - _last_sweep) < min_interval_minutes * 60:
            return
        _last_sweep = time.time()
    sweep_old_materials(retention_hours, data_path=data_path, ocr_output=ocr_output, connection_pool=connection_pool)
