import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch, MagicMock

import configuration
from fakes import FakePool
from use_cases import material_retention_use_case
from use_cases.material_retention_use_case import sweep_if_due, sweep_old_materials


def make_old(path: Path, hours_ago: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("content")
    old = time.time() - hours_ago * 3600
    os.utime(path, (old, old))
    return path


class TestSweepOldMaterials(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.data_path = Path(self.tmp.name)
        self.ocr_output = self.data_path / "ocr_output"
        self.ocr_output.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_old_xml_files_are_deleted_and_fresh_kept(self):
        old = make_old(self.data_path / "t1__old.pdf.xml", 2)
        fresh = self.data_path / "t1__fresh.pdf.xml"
        fresh.parent.mkdir(parents=True, exist_ok=True)
        fresh.write_text("<xml/>")
        legacy = make_old(self.data_path / "default.xml", 2)
        not_xml = make_old(self.data_path / "ignored.txt", 2)

        removed = sweep_old_materials(1, data_path=self.data_path, ocr_output=self.ocr_output)

        self.assertEqual(2, removed)
        self.assertFalse(old.exists())
        self.assertFalse(legacy.exists())
        self.assertTrue(fresh.exists())
        self.assertTrue(not_xml.exists())

    def test_old_ocr_results_are_deleted_recursively_and_empty_tenant_dirs_pruned(self):
        old = make_old(self.ocr_output / "t1" / "old.pdf", 2)
        fresh = self.ocr_output / "t2" / "fresh.pdf"
        fresh.parent.mkdir(parents=True, exist_ok=True)
        fresh.write_text("%PDF-")
        old_other_tenant = make_old(self.ocr_output / "t3" / "old.pdf", 2)

        removed = sweep_old_materials(1, data_path=self.data_path, ocr_output=self.ocr_output)

        self.assertEqual(2, removed)
        self.assertFalse(old.exists())
        self.assertFalse(old_other_tenant.exists())
        self.assertFalse((self.ocr_output / "t3").exists())
        self.assertTrue((self.ocr_output / "t2").exists())
        self.assertTrue(self.ocr_output.exists())

    def test_old_uploaded_pdfs_in_tenant_dirs_are_deleted(self):
        old_pdf = make_old(self.data_path / "t1" / "old.pdf", 2)
        fresh_pdf = self.data_path / "t1" / "fresh.pdf"
        fresh_pdf.parent.mkdir(parents=True, exist_ok=True)
        fresh_pdf.write_text("%PDF-")
        empty_tenant = self.data_path / "t4"
        empty_tenant.mkdir()

        removed = sweep_old_materials(1, data_path=self.data_path, ocr_output=self.ocr_output)

        self.assertEqual(1, removed)
        self.assertFalse(old_pdf.exists())
        self.assertTrue(fresh_pdf.exists())
        self.assertFalse(empty_tenant.exists())

    def test_old_paragraph_rows_are_deleted(self):
        pool = FakePool()

        removed = sweep_old_materials(3, data_path=self.data_path, ocr_output=self.ocr_output, connection_pool=pool)

        self.assertEqual(1, removed)
        sql, params = pool.executed[0]
        self.assertIn("DELETE FROM paragraphs", sql)
        self.assertEqual((3,), params)

    def test_old_paragraph_rows_support_fractional_hours(self):
        pool = FakePool()

        removed = sweep_old_materials(3.5, data_path=self.data_path, ocr_output=self.ocr_output, connection_pool=pool)

        self.assertEqual(1, removed)
        sql, params = pool.executed[0]
        self.assertIn("DELETE FROM paragraphs", sql)
        self.assertIn("interval '1 hour'", sql)
        self.assertEqual((3.5,), params)

    def test_retention_disabled_is_a_noop(self):
        old = make_old(self.data_path / "t1__old.pdf.xml", 100)
        pool = FakePool()

        removed = sweep_old_materials(0, data_path=self.data_path, ocr_output=self.ocr_output, connection_pool=pool)

        self.assertEqual(0, removed)
        self.assertTrue(old.exists())
        self.assertEqual(0, len(pool.executed))

    def test_negative_retention_is_a_noop(self):
        pool = FakePool()
        removed = sweep_old_materials(-1, data_path=self.data_path, ocr_output=self.ocr_output, connection_pool=pool)
        self.assertEqual(0, removed)
        self.assertEqual(0, len(pool.executed))

    def test_one_failing_operation_does_not_stop_the_others(self):
        with patch.object(material_retention_use_case, "_sweep_ocr_output", side_effect=RuntimeError("boom")):
            old = make_old(self.data_path / "t1__old.pdf.xml", 2)

            removed = sweep_old_materials(1, data_path=self.data_path, ocr_output=self.ocr_output)

            self.assertEqual(1, removed)
            self.assertFalse(old.exists())


class TestSweepIfDue(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_runs_at_most_once_per_interval(self):
        with (
            patch.object(material_retention_use_case, "_last_sweep", 0.0),
            patch.object(configuration, "MATERIAL_RETENTION_HOURS", 24.0),
            patch.object(configuration, "MATERIAL_SWEEP_INTERVAL_MINUTES", 10.0),
            patch.object(material_retention_use_case, "sweep_old_materials", return_value=0) as sweep_spy,
        ):
            sweep_if_due(24.0, 10.0, data_path=Path(self.tmp.name))
            sweep_if_due(24.0, 10.0, data_path=Path(self.tmp.name))

            self.assertEqual(1, sweep_spy.call_count)
            self.assertEqual(24.0, sweep_spy.call_args[0][0])

    def test_runs_again_when_interval_elapsed(self):
        with patch.object(material_retention_use_case, "_last_sweep", time.time() - 10000):
            with patch.object(material_retention_use_case, "sweep_old_materials", return_value=0) as sweep_spy:
                sweep_if_due(24.0, 10.0, data_path=Path(self.tmp.name))
                self.assertEqual(1, sweep_spy.call_count)

    def test_no_sweep_when_retention_disabled(self):
        with patch.object(material_retention_use_case, "sweep_old_materials", return_value=0) as sweep_spy:
            sweep_if_due(0, 10.0, data_path=Path(self.tmp.name))
            self.assertEqual(0, sweep_spy.call_count)


class TestEnvFloat(TestCase):
    def test_valid_value(self):
        with patch.dict(os.environ, {"MATERIAL_RETENTION_HOURS": "5.5"}):
            self.assertEqual(5.5, configuration._env_float("MATERIAL_RETENTION_HOURS", 24.0))

    def test_invalid_value_falls_back_to_default(self):
        with patch.dict(os.environ, {"MATERIAL_RETENTION_HOURS": "abc"}):
            self.assertEqual(24.0, configuration._env_float("MATERIAL_RETENTION_HOURS", 24.0))

    def test_unset_value_falls_back_to_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(24.0, configuration._env_float("MATERIAL_RETENTION_HOURS", 24.0))

    def test_invalid_value_logs_a_warning(self):
        with patch.dict(os.environ, {"MATERIAL_RETENTION_HOURS": "abc"}):
            with self.assertLogs(configuration.service_logger, level="WARNING"):
                configuration._env_float("MATERIAL_RETENTION_HOURS", 24.0)


class TestDbMigrations(TestCase):
    def test_run_migrations_executes_idempotent_alter(self):
        from drivers.db_migrations import MIGRATIONS, run_migrations

        pool = FakePool()
        run_migrations(pool)

        self.assertEqual(len(MIGRATIONS), len(pool.executed))
        for (sql, _), expected in zip(pool.executed, MIGRATIONS):
            self.assertEqual(expected, sql)
            self.assertIn("IF NOT EXISTS", sql)
