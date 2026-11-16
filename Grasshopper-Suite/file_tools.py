"""Local, defensive file-integrity helpers; standard library only.

Nothing here executes files, watches the filesystem, or extracts archives. These
helpers are intended for a trusted, quiescent local tree, not as a security
boundary against an adversary concurrently replacing parent directories.
"""
from __future__ import annotations

import hashlib
import ntpath
import os
from pathlib import Path, PurePosixPath
import stat
import zipfile


class FileToolError(Exception):
    """A file could not be safely processed or changed during processing."""


def _positive_int(name, value, *, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, int) or value < (0 if allow_zero else 1):
        raise ValueError(f"{name} must be {'a non-negative' if allow_zero else 'a positive'} integer")


def _signature(st):
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _open_regular(path):
    """Open only an ordinary file, rejecting a symlink in the final component."""
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode):
        raise FileToolError(f"not a regular file (symlinks are not followed): {path}")
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    try:
        after = os.fstat(fd)
        if not stat.S_ISREG(after.st_mode) or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise FileToolError(f"file changed while opening: {path}")
        return os.fdopen(fd, 'rb'), after
    except BaseException:
        os.close(fd)
        raise


def sha256_file(path, *, chunk_size=1024 * 1024, max_bytes=None):
    """Return a lowercase SHA-256 hex digest, reading a regular file in chunks.

    Symlinks and special files are rejected. max_bytes, if set, is a hard read
    limit. Raise FileToolError if the file changes or exceeds that limit; OS
    access errors propagate as OSError. Parent symlinks are not prohibited.
    """
    _positive_int('chunk_size', chunk_size)
    if max_bytes is not None:
        _positive_int('max_bytes', max_bytes, allow_zero=True)
    stream, initial = _open_regular(path)
    with stream:
        if max_bytes is not None and initial.st_size > max_bytes:
            raise FileToolError(f"file exceeds max_bytes: {path}")
        digest = hashlib.sha256()
        total = 0
        while True:
            # Read one extra byte at the boundary to detect growth, if needed.
            length = chunk_size if max_bytes is None else min(chunk_size, max_bytes - total + 1)
            data = stream.read(length)
            if not data:
                break
            total += len(data)
            if max_bytes is not None and total > max_bytes:
                raise FileToolError(f"file exceeds max_bytes: {path}")
            digest.update(data)
        if _signature(initial) != _signature(os.fstat(stream.fileno())) or total != initial.st_size:
            raise FileToolError(f"file changed during hashing: {path}")
        return digest.hexdigest()


def file_metadata(path):
    """Return lstat metadata without following the final symlink.

    Keys: type (file/directory/symlink/other), size, mode (permission bits),
    mtime_ns. OSError propagates for inaccessible or missing paths.
    """
    st = os.lstat(path)
    kind = ('file' if stat.S_ISREG(st.st_mode) else 'directory' if stat.S_ISDIR(st.st_mode)
            else 'symlink' if stat.S_ISLNK(st.st_mode) else 'other')
    return {'type': kind, 'size': st.st_size, 'mode': stat.S_IMODE(st.st_mode), 'mtime_ns': st.st_mtime_ns}


def directory_manifest(root, *, max_entries=10000, max_total_bytes=1024**3,
                       max_file_bytes=256 * 1024**2, max_depth=32, chunk_size=1024 * 1024):
    """Hash a directory tree, without following symlinks or special files.

    Return {'root', 'files', 'errors', 'complete', 'entries_seen', 'bytes_hashed'}.
    files maps POSIX relative paths to {'sha256', 'size', 'mtime_ns', 'mode'}.
    errors holds {'path', 'error'} records. Limits are finite by default; any
    skip/error makes complete false. Entry limit counts files, dirs and links.
    max_depth=0 means only files directly in root (child dirs are skipped).
    Tree iteration is not a filesystem snapshot; concurrent mutation can affect
    results, and ancestor-directory symlink races cannot be fully prevented.
    """
    _positive_int('max_entries', max_entries)
    for name, value in [('max_total_bytes', max_total_bytes), ('max_file_bytes', max_file_bytes), ('max_depth', max_depth)]:
        _positive_int(name, value, allow_zero=True)
    _positive_int('chunk_size', chunk_size)
    root = Path(os.path.abspath(os.fspath(root)))
    result = {'root': str(root), 'files': {}, 'errors': [], 'complete': True,
              'entries_seen': 0, 'bytes_hashed': 0}

    def error(path, message):
        result['errors'].append({'path': path, 'error': str(message)})
        result['complete'] = False

    try:
        root_stat = os.lstat(root)
        if not stat.S_ISDIR(root_stat.st_mode):
            raise FileToolError('root must be a directory, not a symlink or special file')
    except (OSError, FileToolError) as exc:
        error('.', exc)
        return result

    stack = [(root, '', 0)]
    stop = False
    while stack and not stop:
        directory, prefix, depth = stack.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    rel = f'{prefix}/{entry.name}' if prefix else entry.name
                    if result['entries_seen'] >= max_entries:
                        error(rel, 'max_entries exceeded; scan stopped')
                        stop = True
                        break
                    result['entries_seen'] += 1
                    try:
                        info = entry.stat(follow_symlinks=False)
                        if stat.S_ISLNK(info.st_mode):
                            error(rel, 'symlink skipped')
                        elif stat.S_ISDIR(info.st_mode):
                            if depth >= max_depth:
                                error(rel, 'max_depth exceeded; directory skipped')
                            else:
                                stack.append((Path(entry.path), rel, depth + 1))
                        elif stat.S_ISREG(info.st_mode):
                            if info.st_size > max_file_bytes:
                                error(rel, 'max_file_bytes exceeded; file skipped')
                                continue
                            remaining = max_total_bytes - result['bytes_hashed']
                            if info.st_size > remaining:
                                error(rel, 'max_total_bytes exceeded; file skipped')
                                continue
                            digest = sha256_file(entry.path, chunk_size=chunk_size,
                                                 max_bytes=min(max_file_bytes, remaining))
                            after = os.lstat(entry.path)
                            if _signature(info) != _signature(after) or not stat.S_ISREG(after.st_mode):
                                raise FileToolError('file changed during manifest scan')
                            result['files'][rel] = {'sha256': digest, 'size': info.st_size,
                                                    'mtime_ns': info.st_mtime_ns,
                                                    'mode': stat.S_IMODE(info.st_mode)}
                            result['bytes_hashed'] += info.st_size
                        else:
                            error(rel, 'special file skipped')
                    except (OSError, FileToolError) as exc:
                        error(rel, exc)
        except OSError as exc:
            error(prefix or '.', exc)
    result['files'] = dict(sorted(result['files'].items()))
    return result


def compare_manifests(old, new, *, allow_incomplete=False):
    """Compare manifest file hashes. Return sorted added/removed/changed paths.

    'changed' means SHA-256 differs, not metadata-only changes. By default,
    reject incomplete scans to avoid presenting partial results as conclusive.
    """
    if not allow_incomplete and (old.get('complete') is not True or new.get('complete') is not True):
        raise ValueError('cannot compare incomplete manifests unless allow_incomplete=True')
    a, b = old['files'], new['files']
    ka, kb = set(a), set(b)
    return {'added': sorted(kb - ka), 'removed': sorted(ka - kb),
            'changed': sorted(p for p in ka & kb if a[p]['sha256'] != b[p]['sha256'])}


def inspect_zip(path, *, max_archive_bytes=64 * 1024**2, max_entries=10000,
                max_uncompressed_bytes=1024**3):
    """Inspect ZIP metadata only; never extract, execute, or decompress members.

    Return entries (name, sizes, flags), warnings, complete and total declared
    uncompressed bytes. Limits are safeguards, not proof a ZIP is safe. ZIP's
    central directory is loaded by the standard library, so archive byte size
    is bounded *before* parsing. Reports suspicious paths, links, encryption,
    duplicate names and size/entry limits; malformed ZIP/OSError propagates.
    """
    for name, value in [('max_archive_bytes', max_archive_bytes), ('max_entries', max_entries),
                        ('max_uncompressed_bytes', max_uncompressed_bytes)]:
        _positive_int(name, value, allow_zero=True)
    stream, initial = _open_regular(path)
    result = {'entries': [], 'warnings': [], 'complete': True, 'total_uncompressed_bytes': 0}
    with stream:
        if initial.st_size > max_archive_bytes:
            raise FileToolError('archive exceeds max_archive_bytes')
        with zipfile.ZipFile(stream) as archive:
            seen = set()
            for info in archive.infolist():
                if len(result['entries']) >= max_entries:
                    result['warnings'].append('max_entries exceeded; inspection stopped')
                    result['complete'] = False
                    break
                name = info.filename
                normalized = name.replace('\\', '/')
                parts = PurePosixPath(normalized).parts
                suspicious = (not name or '\x00' in name or normalized.startswith('/') or
                              bool(ntpath.splitdrive(name)[0]) or '..' in parts or '\\' in name)
                unix_mode = info.external_attr >> 16 if info.create_system == 3 else 0
                kind = stat.S_IFMT(unix_mode)
                is_link = kind == stat.S_IFLNK
                special = kind not in (0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK)
                flags = []
                if suspicious: flags.append('unsafe_path')
                if is_link: flags.append('symlink')
                if special: flags.append('special_file')
                if info.flag_bits & 1: flags.append('encrypted')
                if name in seen: flags.append('duplicate_name')
                seen.add(name)
                result['total_uncompressed_bytes'] += info.file_size
                result['entries'].append({'name': name, 'compressed_size': info.compress_size,
                                          'uncompressed_size': info.file_size, 'flags': flags})
                if result['total_uncompressed_bytes'] > max_uncompressed_bytes:
                    result['warnings'].append('max_uncompressed_bytes exceeded; inspection stopped')
                    result['complete'] = False
                    break
        if _signature(initial) != _signature(os.fstat(stream.fileno())):
            raise FileToolError('archive changed during inspection')
    return result
