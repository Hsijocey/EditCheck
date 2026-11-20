"""Verify files recorded in an EditCheck research-figure manifest."""

from hashlib import sha256
import json
from pathlib import Path
import re

from .rules import Issue


def fingerprint(path):
    with Path(path).open('rb') as stream:
        digest = sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _file_entry(entry, root):
    if not isinstance(entry, dict):
        raise ValueError('Each file entry needs a relative path and SHA-256.')
    name, digest = entry.get('path'), entry.get('sha256')
    if not isinstance(name, str) or not name or Path(name).anchor:
        raise ValueError('File paths must be relative to the manifest.')
    if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', digest):
        raise ValueError('Every file must have a 64-digit SHA-256.')
    path = (root / name).resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError('A file path leaves the manifest directory.')
    return name, path, digest.lower()


def _check_file(entry, root, label, kind):
    name, path, expected = _file_entry(entry, root)
    try:
        actual = fingerprint(path)
    except FileNotFoundError:
        return Issue('RESEARCH_FILE_MISSING', label, f'{kind} is missing: {name}.')
    except OSError:
        return Issue('RESEARCH_FILE_UNREADABLE', label, f'{kind} could not be read: {name}.')
    if actual != expected:
        return Issue('RESEARCH_FILE_CHANGED', label, f'{kind} changed since the recorded build: {name}.')
    return None


def check_manifest(manifest_path):
    path = Path(manifest_path).resolve()
    try:
        manifest = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 1:
            raise ValueError('Expected schema_version 1.')
        figures = manifest.get('figures')
        if not isinstance(figures, list) or not figures:
            raise ValueError('The manifest needs at least one figure.')
        issues = []
        for figure in figures:
            if not isinstance(figure, dict) or not isinstance(figure.get('name'), str) or not figure['name'].strip():
                raise ValueError('Each figure needs a name.')
            name = figure['name']
            inputs = figure.get('inputs')
            if not isinstance(inputs, list) or not inputs:
                raise ValueError(f'{name} needs at least one input.')
            entries = [(figure.get('artifact'), 'Figure'), (figure.get('script'), 'Generator')]
            entries.extend((entry, 'Input') for entry in inputs)
            for entry, kind in entries:
                issue = _check_file(entry, path.parent, name, kind)
                if issue:
                    issues.append(issue)
        return tuple(issues)
    except (ValueError, UnicodeError, OSError, RuntimeError) as error:
        detail = 'The selected manifest could not be read.' if isinstance(error, OSError) else str(error)
        return (Issue('MANIFEST_INVALID', path.name, detail),)
