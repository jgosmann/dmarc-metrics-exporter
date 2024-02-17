#!/usr/bin/env python3

import argparse

from packaging.version import parse as parse_version

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Check whether a version is a prerelease according to PEP440."
    )
    arg_parser.add_argument("version")
    args = arg_parser.parse_args()

    if parse_version(args.version).is_prerelease:
        print("PRERELEASE=true")
    else:
        print("PRERELEASE=false")
