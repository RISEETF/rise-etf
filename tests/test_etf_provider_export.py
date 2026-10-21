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
    def fixture_rows(self):
        return [module.FUNETF_KR_HEADER[:],
                ['RISE 테스트', '254H0'.zfill(6), '국내주식'] + ['1']*12 +
                ['KB운용', '종목 A', '12', '종목 B', '7', '종목 C', '3']]

    def test_normalization_preserves_alphanumeric_codes_and_holding_weights(self):
        rows = self.fixture_rows()
        record = module.normalize_funetf_kr(rows)[0]
        self.assertEqual(record['code'], '0254H0')
        self.assertEqual([r['weight_pct'] for r in record['holdings_top3']], [12, 7, 3])
        self.assertEqual(module.normalize_kr_code('69500'), '069500')
        with self.assertRaisesRegex(ValueError, 'CODE_INVALID'):
            module.normalize_kr_code('AAPL')
        rows.append(rows[1][:])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_CODE'):
            module.normalize_funetf_kr(rows)

    def test_schema_and_numbers_fail_closed(self):
        rows = self.fixture_rows(); rows[0][17] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'SCHEMA_UNSUPPORTED'):
            module.normalize_funetf_kr(rows)
        rows = self.fixture_rows(); rows[1][3] = 'NaN'
        with self.assertRaisesRegex(ValueError, 'NONFINITE'):
            module.normalize_funetf_kr(rows)
        rows[1][3] = '-'; rows[1][10] = '-1'
        with self.assertRaisesRegex(ValueError, 'NEGATIVE_FEE'):
            module.normalize_funetf_kr(rows)

    def test_inspection_preserves_primary_and_marks_dates_unknown(self):
        import csv
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)/'sample.csv'
            with p.open('w') as f: csv.writer(f).writerows(self.fixture_rows())
            inventory = {'observed_on': '2026-10-20', 'observed_count': 2,
                         'raw_sha256': 'test', 'products': [
                {'code': '0254H0', 'name': 'RISE 테스트', 'status': 'OBSERVED', 'last_observed_on': '2026-10-20'},
                {'code': '000001', 'name': 'RISE 신규', 'status': 'OBSERVED', 'last_observed_on': '2026-10-20'}]}
            original = json.dumps(inventory)
            report = module.inspect_funetf_kr(p, inventory)
            self.assertEqual(report['date_comparison'], 'UNKNOWN')
            self.assertEqual(report['missing_from_provider'][0]['code'], '000001')
            self.assertFalse(report['publication_eligible'])
            self.assertEqual(json.dumps(inventory), original)
            self.assertEqual(len(list(pathlib.Path(d).iterdir())), 1)
            self.assertEqual(module.inspect_funetf_kr(p, inventory, '2026-10-19')['date_comparison'], 'DIFFERENT_DATES')

    def test_xlsx_wrong_dimensions_read_all_columns(self):
        # Synthetic OOXML fixture, no provider data or authored user workbook.
        import importlib.util
        if importlib.util.find_spec('openpyxl') is None:
            self.skipTest('XLSX dependency is installed in provider CI')
        from zipfile import ZipFile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)/'fixture.xlsx'
            with ZipFile(p, 'w') as z:
                z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
                z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Fixture" sheetId="1" r:id="rId1"/></sheets></workbook>')
                z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
                z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:A1"/><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>code</t></is></c><c r="B1" t="inlineStr"><is><t>name</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>0254H0</t></is></c><c r="B2" t="inlineStr"><is><t>ETF</t></is></c></row></sheetData></worksheet>')
            rows, encoding = module.read_rows(p)
            self.assertEqual(rows, [['code', 'name'], ['0254H0', 'ETF']])

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
