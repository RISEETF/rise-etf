"""Offline tests for the optional ETFcheck/FunETF file archive."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "import_etf_provider_export.py"
spec = importlib.util.spec_from_file_location("provider_importer", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProviderExportTests(unittest.TestCase):
    def test_csv_archive_and_idempotency(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            sample = root / "sample.csv"
            sample.write_text("종목코드,종목명,가격\n069500,ETF A,100\n", encoding="utf-8-sig")
            first = module.ingest(sample, "etfcheck", "2026-10-20", root / "archive")
            second = module.ingest(sample, "etfcheck", "2026-10-20", root / "archive")
            self.assertEqual(first["sha256"], second["sha256"])
            manifest = json.loads((pathlib.Path(first["archive_path"]) / "manifest.json").read_text())
            self.assertFalse(manifest["publication_eligible"])
            self.assertEqual(manifest["status"], "QUARANTINED")
            self.assertTrue((pathlib.Path(first["archive_path"]) / "original.csv").is_file())

    def test_reject_empty_data(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            sample = root / "empty.csv"
            sample.write_text("종목코드,종목명\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "NO_DATA_ROWS"):
                module.ingest(sample, "funetf", "2026-10-20", root / "archive")

    def test_reject_unsupported_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            sample = root / "sample.csv"
            sample.write_text("a,b\n1,2\n")
            with self.assertRaisesRegex(ValueError, "SOURCE_NOT_SUPPORTED"):
                module.ingest(sample, "unknown", "2026-10-20", root / "archive")


if __name__ == "__main__":
    unittest.main()
