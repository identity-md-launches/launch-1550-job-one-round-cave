"""Offline checks for the split account and runtime-code handoff."""
import hashlib
import io
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
import zipfile

import code_extension as tool


HERE = Path(__file__).resolve().parent


class CodeExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.account = (HERE / 'examples/zto-proof.zip').read_bytes()
        cls.code = (HERE / 'examples/zto-code.json').read_bytes()
        cls.extension = (HERE / 'examples/zto-code-extension.zip').read_bytes()

    def repack(self, changes):
        with zipfile.ZipFile(io.BytesIO(self.extension)) as archive:
            files = {name: archive.read(name) for name in tool.PATHS}
        files.update(changes)
        return tool.base.writer.build(files)

    def test_real_pair_and_reproducibility(self):
        self.assertEqual(tool.build(self.account, self.code), self.extension)
        result = tool.inspect_bytes(self.account, self.extension)
        self.assertTrue(result['verified'])
        self.assertEqual(result['code']['bytecode_bytes'], 1287)
        self.assertEqual(result['code']['proved_code_hash'],
                         '0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d')

    def test_no_network_demo(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('socket used')):
            self.assertTrue(tool.demo()['verified'])

    def test_changed_code_rejected(self):
        value = json.loads(self.code)
        raw = value['result']
        value['result'] = '0x00' + raw[4:]
        with self.assertRaises(ValueError):
            tool.build(self.account, tool.canonical(value))

    def test_tampered_rehashed_report_rejected(self):
        false = tool.canonical({'verified': True})
        with self.assertRaises(ValueError):
            tool.inspect_bytes(self.account, self.repack({tool.REPORT: false}))

    def test_wrong_account_link_rejected(self):
        link = tool.canonical({'schema': 'zto-code-extension-link/1',
                               'account_archive_sha256': '0' * 64})
        with self.assertRaises(ValueError):
            tool.inspect_bytes(self.account, self.repack({tool.LINK: link}))

    def test_missing_payload_rejected(self):
        with zipfile.ZipFile(io.BytesIO(self.extension)) as archive:
            files = {name: archive.read(name) for name in tool.PATHS - {tool.CODE}}
        with self.assertRaises(ValueError):
            tool.inspect_bytes(self.account, tool.base.writer.build(files))

    def test_account_and_extension_digests_checked(self):
        a = hashlib.sha256(self.account).hexdigest()
        e = hashlib.sha256(self.extension).hexdigest()
        self.assertTrue(tool.inspect_bytes(self.account, self.extension, a, e)['verified'])
        with self.assertRaises(ValueError):
            tool.inspect_bytes(self.account, self.extension, '0' * 64, e)
        with self.assertRaises(ValueError):
            tool.inspect_bytes(self.account, self.extension, a, '0' * 64)

    def test_corrupt_account_archive_rejected(self):
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            tool.inspect_bytes(self.account[:-1], self.extension)


if __name__ == '__main__':
    unittest.main()
