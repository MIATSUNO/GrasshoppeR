import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import file_tools as ft


class FileToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, data):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def test_streamed_sha256_known_values_and_bounds(self):
        p = self.put('a', b'abc')
        self.assertEqual(ft.sha256_file(p, chunk_size=1), hashlib.sha256(b'abc').hexdigest())
        self.assertEqual(ft.sha256_file(p, max_bytes=3), hashlib.sha256(b'abc').hexdigest())
        with self.assertRaises(ft.FileToolError):
            ft.sha256_file(p, max_bytes=2)
        empty = self.put('empty', b'')
        self.assertEqual(ft.sha256_file(empty, max_bytes=0), hashlib.sha256(b'').hexdigest())
        with self.assertRaises(ValueError):
            ft.sha256_file(p, chunk_size=0)
        with self.assertRaises(ValueError):
            ft.sha256_file(p, max_bytes=-1)
        with self.assertRaises(OSError):
            ft.sha256_file(self.root / 'missing')

    def test_metadata_types_and_symlink_rejection(self):
        p = self.put('target', b'1234')
        self.assertEqual(ft.file_metadata(p)['type'], 'file')
        self.assertEqual(ft.file_metadata(p)['size'], 4)
        self.assertEqual(ft.file_metadata(self.root)['type'], 'directory')
        link = self.root / 'link'
        try:
            link.symlink_to(p)
        except (OSError, NotImplementedError):
            self.skipTest('symlink creation unavailable')
        self.assertEqual(ft.file_metadata(link)['type'], 'symlink')
        with self.assertRaises(ft.FileToolError):
            ft.sha256_file(link)
        with self.assertRaises(ft.FileToolError):
            ft.sha256_file(self.root)

    def test_manifest_comparison_add_remove_change(self):
        self.put('removed', b'old')
        self.put('changed', b'old')
        self.put('nested/unchanged', b'keep')
        a = ft.directory_manifest(self.root, chunk_size=2)
        self.assertTrue(a['complete'], a['errors'])
        self.assertEqual(a['files']['nested/unchanged']['size'], 4)
        (self.root / 'removed').unlink()
        self.put('changed', b'new')
        self.put('added', b'new')
        b = ft.directory_manifest(self.root)
        self.assertTrue(b['complete'], b['errors'])
        self.assertEqual(ft.compare_manifests(a, b),
                         {'added': ['added'], 'removed': ['removed'], 'changed': ['changed']})
        self.assertEqual(b['bytes_hashed'], 10)

    def test_manifest_symlinks_and_special_are_skipped(self):
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        outside = Path(external.name) / 'secret'
        outside.write_text('secret')
        self.put('safe', b'x')
        try:
            (self.root / 'outside').symlink_to(external.name, target_is_directory=True)
            (self.root / 'link').symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest('symlink creation unavailable')
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.root / 'fifo')
        m = ft.directory_manifest(self.root)
        self.assertFalse(m['complete'])
        self.assertEqual(list(m['files']), ['safe'])
        errors = {e['path']: e['error'] for e in m['errors']}
        self.assertIn('symlink', errors['outside'])
        self.assertIn('symlink', errors['link'])
        if hasattr(os, 'mkfifo'):
            self.assertIn('special', errors['fifo'])
        with self.assertRaises(ValueError):
            ft.compare_manifests(m, m)
        self.assertEqual(ft.compare_manifests(m, m, allow_incomplete=True)['changed'], [])
        self.assertFalse(ft.directory_manifest(self.root / 'outside')['complete'])

    def test_manifest_limits_and_bad_root(self):
        self.put('large', b'12345')
        self.put('nested/a', b'123')
        m = ft.directory_manifest(self.root, max_file_bytes=4, max_depth=0)
        self.assertFalse(m['complete'])
        self.assertEqual(m['files'], {})
        self.assertEqual(len(m['errors']), 2)
        m = ft.directory_manifest(self.root, max_total_bytes=0)
        self.assertFalse(m['complete'])
        self.assertEqual(m['bytes_hashed'], 0)
        m = ft.directory_manifest(self.root, max_entries=1)
        self.assertFalse(m['complete'])
        self.assertEqual(m['entries_seen'], 1)
        self.assertTrue(any('max_entries' in x['error'] for x in m['errors']))
        self.assertFalse(ft.directory_manifest(self.root / 'missing')['complete'])
        with self.assertRaises(ValueError):
            ft.directory_manifest(self.root, max_depth=-1)

    def test_inspect_zip_flags_and_no_extraction(self):
        p = self.root / 'sample.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('good.txt', 'safe')
                z.writestr('../escape.txt', 'bad')
                z.writestr('/absolute', 'bad')
                z.writestr('C:\\windows', 'bad')
                z.writestr('good.txt', 'duplicate')
                info = zipfile.ZipInfo('link')
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, 'target')
        report = ft.inspect_zip(p)
        self.assertTrue(report['complete'])
        self.assertEqual(len(report['entries']), 6)
        self.assertEqual(report['entries'][0]['flags'], [])
        for i in (1, 2, 3):
            self.assertIn('unsafe_path', report['entries'][i]['flags'])
        self.assertIn('duplicate_name', report['entries'][4]['flags'])
        self.assertIn('symlink', report['entries'][5]['flags'])
        self.assertFalse((self.root / 'good.txt').exists())
        self.assertFalse((self.root.parent / 'escape.txt').exists())

    def test_zip_limits_invalid_and_no_follow(self):
        p = self.root / 'archive.zip'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('one', 'abc')
            z.writestr('two', 'def')
        self.assertFalse(ft.inspect_zip(p, max_entries=1)['complete'])
        m = ft.inspect_zip(p, max_uncompressed_bytes=2)
        self.assertFalse(m['complete'])
        self.assertEqual(m['total_uncompressed_bytes'], 3)
        with self.assertRaises(ft.FileToolError):
            ft.inspect_zip(p, max_archive_bytes=1)
        bad = self.put('bad.zip', b'not a ZIP')
        with self.assertRaises(zipfile.BadZipFile):
            ft.inspect_zip(bad)
        with self.assertRaises(ValueError):
            ft.inspect_zip(p, max_entries=-1)
        try:
            (self.root / 'archive-link').symlink_to(p)
        except (OSError, NotImplementedError):
            return
        with self.assertRaises(ft.FileToolError):
            ft.inspect_zip(self.root / 'archive-link')


if __name__ == '__main__':
    unittest.main()
