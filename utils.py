from typing import Optional
import re
import requests


def file_contents(file_path: str, verbose: bool = False) -> Optional[str]:
    """
    Load file contents into a string

    Args:
        file_path: Path or URL of source file
        verbose: Whether to display debug notes

    Returns:
        File contents as string
    """
    contents = None

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


def fix_high_unicode(input: str) -> str:
    """
    Replace any remaining \u0123 sequences with correct UTF8 symbol

    Args:
        input: Potentially escaped string

    Returns:
        unescaped string

    """

    def uc(n):
        fix = chr(int(n[1], 16))
        print('Replace', n, 'with', fix)
        return fix

    print('fhu: check : ', input)

    return re.sub(r'\\u([0-9a-f]{4})', uc, input)
