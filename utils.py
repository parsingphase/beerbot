from typing import Optional, TextIO
import csv
import re
import requests

try:
    from config import config
except ImportError:
    config = {}


def file_contents(file_path: str, verbose: bool = False) -> Optional[str]:
    """
    Load file contents into a string

    Args:
        file_path: Path or URL of source file
        verbose: Whether to display debug notes

    Returns:
        File contents as string
    """

    match = re.match('^(f|ht)tp(s?)://', file_path)
    if match:
        if verbose:
            print("Fetch from URL")
        r = requests.get(file_path)
        contents = r.content.decode('utf-8')  # string
    else:
        if verbose:
            print("Load from file")
        with open(file_path, 'r') as f:
            contents = f.readlines()

    if contents and verbose:
        print(contents)

    return ''.join(contents)


def fix_high_unicode(suspect_string: str) -> str:
    """
    Replace any remaining \u0123 sequences with correct UTF8 symbol

    Args:
        suspect_string: Potentially escaped string

    Returns:
        unescaped string

    """

    def uc(n):
        fix = chr(int(n[1], 16))
        print('Replace', n, 'with', fix)
        return fix

    print('fhu: check : ', suspect_string)

    return re.sub(r'\\u([0-9a-f]{4})', uc, suspect_string)


def build_csv_from_list(stocklist: list, stocklist_output: TextIO):
    writer = csv.writer(stocklist_output)
    for row in stocklist:
        writer.writerow(row)


def get_config(key: str, default=None):
    """
    Get the specifed config key if available

    Args:
        key:
        default:

    Returns:

    """
    return config.get(key, default)
