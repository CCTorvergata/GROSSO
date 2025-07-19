import argparse
from config import DEFAULT_MAX_FILE_SIZE_KB, REQUEST_TIMEOUT_SECONDS

def parse_args():
    parser = argparse.ArgumentParser(
        description="Recursively collect readable or executable files from a directory and analyze them for CTF vulnerabilities."
    )
    parser.add_argument(
        '-p', '--path',
        required=True,
        help="Root directory path to scan for files."
    )
    parser.add_argument(
        '-ms', '--maxsize',
        type=int,
        default=DEFAULT_MAX_FILE_SIZE_KB, # Use default from config
        help=f"Max file size in KB (default: {DEFAULT_MAX_FILE_SIZE_KB})"
    )
    parser.add_argument(
        '-t', '--timeout',
        type=int,
        default=REQUEST_TIMEOUT_SECONDS, # Use default from config
        help=f"Timeout for model response in seconds (default: {REQUEST_TIMEOUT_SECONDS})"
    )
    return parser.parse_args()