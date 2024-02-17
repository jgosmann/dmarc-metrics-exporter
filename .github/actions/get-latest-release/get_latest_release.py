#!/usr/bin/env python3

import argparse

import requests
from packaging.version import parse as parse_version

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Get the latest non-prerelease version of a package according to PEP440."
    )
    arg_parser.add_argument("package")
    args = arg_parser.parse_args()

    r = requests.get(
        f"https://pypi.org/simple/{args.package}",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
        timeout=30,
    )
    r.raise_for_status()
    versions = [parse_version(v) for v in r.json().get("versions", [])]
    latest = max(v for v in versions if not v.is_prerelease)
    if latest:
        print(f"VERSION={latest}")
