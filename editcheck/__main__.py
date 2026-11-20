"""Check a research manifest from an ordinary Python installation."""

import argparse

from .provenance import check_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', help='Path to an EditCheck research-figure manifest')
    issues = check_manifest(parser.parse_args().manifest)
    if not issues:
        print('OK: recorded research files match the manifest.')
        return 0
    for issue in issues:
        print(f'{issue.code} | {issue.subject} | {issue.detail}')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
