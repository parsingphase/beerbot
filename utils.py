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


def debug_print(message):
    if get_config('debug'):
        print(message)


def filter_source_data(filter_strings: list, source_data: list, verbose: bool = False):
    """
    Filter source data according to a list of rules
    Args:
        filter_strings: The rules in simple string format
        source_data: JSON source data from export
        verbose: Emit debug if true

    Returns:
        Filtered source data
    """

    ruleset = []

    def create_test_function(key: str, comparator: str, value: str):

        def test_empty(row):
            result = row[key] is None or row[key] == ''
            if verbose:
                print('Check [%s] (%s) is None: %s' % (key, row[key], repr(result)))
            return result

        def test_equals(row):
            result = row[key] is not None and row[key].lower() == value.lower()
            if verbose:
                print('Check [%s] (%s) = %s: %s' % (key, row[key], value, repr(result)))
            return result

        def test_greater(row):
            result = row[key] is not None and row[key].lower() > value.lower()
            if verbose:
                print('Check [%s] (%s) > %s: %s' % (key, row[key], value, repr(result)))
            return result

        def test_less(row):
            result = row[key] is not None and row[key].lower() < value.lower()
            if verbose:
                print('Check [%s] (%s) < %s: %s' % (key, row[key], value, repr(result)))
            return result

        def test_starts(row):
            result = row[key] is not None and row[key].lower().find(value.lower()) == 0
            if verbose:
                print('Check [%s] (%s) ~ %s: %s' % (key, row[key], value, repr(result)))
            return result

        def test_not(row):
            result = row[key] is None or row[key].lower() != value.lower()
            if verbose:
                print('Check [%s] (%s) ^ %s: %s' % (key, row[key], value, repr(result)))
            return result

        def test_contains(row):
            result = value.lower() in row[key].lower() if key in row and row[key] else False
            if verbose:
                print('Check [%s] (%s) ^ %s: %s' % (key, row[key], value, repr(result)))
            return result

        if comparator == '=':
            if value == '':
                test = test_empty
            else:
                test = test_equals
        elif comparator == '>':
            test = test_greater
        elif comparator == '<':
            test = test_less
        elif comparator == '~':
            test = test_starts
        elif comparator == '?':
            test = test_contains
        elif comparator == '^':
            test = test_not
        else:
            raise Exception('Bad rule comparator ' + comparator)

        return test

    for filter_string in filter_strings:
        parts = re.match(r'(?P<key>[a-z_]+)(?P<comparator>[=<>~?^])(?P<value>.*)', filter_string)

        if parts is None:
            raise Exception('Failed to parse rule: ' + filter_string)

        ruleset.append({'test': create_test_function(**parts.groupdict()), 'filter': parts.groupdict()})

    def input_filter(row):
        result = True
        for rule in ruleset:
            if not rule['test'](row):
                result = False
                break

        return result

    source_data = [row for row in source_data if input_filter(row)]
    return source_data
