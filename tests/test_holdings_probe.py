import io
import json
import socket
import ssl
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from probe_etf_holdings import failure_reason, probe


class HoldingsProbeTests(unittest.TestCase):
    def test_safe_failure_categories(self):
        cases = [(TimeoutError('secret'), 'CONNECTION_TIMEOUT'),
                 (socket.gaierror('secret'), 'DNS_FAILURE'),
                 (ssl.SSLError('secret'), 'TLS_FAILURE'),
                 (ConnectionRefusedError('secret'), 'CONNECTION_FAILURE')]
        for exc, expected in cases:
            self.assertEqual(failure_reason(urllib.error.URLError(exc)), expected)
        self.assertEqual(failure_reason(urllib.error.URLError('secret')), 'UNCLASSIFIED_FETCH_FAILURE')
        self.assertEqual(failure_reason(ValueError('secret')), 'UNCLASSIFIED_FETCH_FAILURE')
        self.assertEqual(failure_reason(json.JSONDecodeError('secret', '', 0)), 'INVALID_JSON')

    def test_probe_never_promotes_received_json(self):
        queue = {'schema': 'ETF_INVESTIGATION_QUEUE_V1', 'observation_date': '2026-10-30',
                 'items': [{'ticker': '0164G0', 'name': 'RISE test'}]}
        master = {'products': [{'code': '0164G0', 'name': 'RISE test', 'detail_id': '1234'}]}
        for response, expected in [(io.BytesIO(b'{"holdings": []}'), 'JSON_RECEIVED_UNVALIDATED'),
                                   (urllib.error.URLError(TimeoutError('secret')), 'FETCH_FAILED')]:
            with tempfile.TemporaryDirectory() as directory:
                kwargs = {'side_effect': response} if isinstance(response, Exception) else {'return_value': response}
                with patch('urllib.request.urlopen', **kwargs) as fetch:
                    report = probe(queue, master, directory)
                self.assertEqual(fetch.call_count, 1)
                self.assertEqual(report['items'][0]['status'], expected)
                self.assertFalse(report['production_enabled'])
                self.assertFalse(report['items'][0]['holdings_verified'])
                self.assertNotIn('secret', Path(directory, 'probe.json').read_text())

    def test_oversized_shortlist_makes_no_requests(self):
        with tempfile.TemporaryDirectory() as directory, patch('urllib.request.urlopen') as fetch:
            with self.assertRaises(ValueError):
                probe({'schema': 'ETF_INVESTIGATION_QUEUE_V1', 'items': [{}] * 6}, {}, directory)
            fetch.assert_not_called()
