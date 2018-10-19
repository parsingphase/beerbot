#!/usr/bin/env python

import argparse
import csv
import sys
import json
from typing import Optional
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import TextIO


def file_contents(file_path: str) -> Optional[str]:
    """
    Load file contents into a string

    Args:
        file_path: Path of source file

    Returns:
        File contents as string
    """
    with open(file_path, 'r') as f:
        contents = f.readlines()
    return ''.join(contents)


def build_dated_stocklist(source_data: list, stocklist_output: TextIO = None, styles_output: TextIO = None) -> None:
    """
    Convert the parsed JSON from a list feed into a CSV reporting stock levels and expiry

    Args:
        source_data: json data parsed into a list
        stocklist_output: buffer to write stock list to
        styles_output: buffer to write styles summary to
    """
    source_data.sort(key=lambda b: b['best_by_date_iso'])
    thresholds = [
        {'description': 'Undated beers', 'ends': '0000-00-00'},
        {'description': 'Expired beers', 'ends': date.today().strftime('%Y-%m-%d')},
        {'description': 'Within one month', 'ends': (date.today() + relativedelta(months=+1)).strftime('%Y-%m-%d')},
        {'description': 'Within two months', 'ends': (date.today() + relativedelta(months=+2)).strftime('%Y-%m-%d')},
        {'description': 'More than two months away'}
    ]
    slices = [[] for _ in range(len(thresholds))]
    styles = {}
    for item in source_data:
        style = item['beer_type'].split(' -')[0].strip()
        if style not in styles:
            styles[style] = 0
        styles[style] += int(item['quantity'])

        due = item['best_by_date_iso']

        for idx, threshold in enumerate(thresholds):
            if 'ends' in threshold and due <= threshold['ends']:
                slices[idx].append(item)
                break

            if 'ends' not in threshold:
                slices[idx].append(item)

    style_list = []
    for style in styles:
        style_list.append({'style': style, 'count': styles[style]})
    style_list.sort(key=lambda b: (0 - b['count'], b['style']))

    if stocklist_output:
        writer = csv.writer(stocklist_output)
        for k, drinks in enumerate(slices):
            writer.writerow(
                [
                    '%s: %d item(s) of %d beer(s)' % (
                        thresholds[k]['description'], sum([int(drink['quantity']) for drink in drinks]), len(drinks),
                    )
                ]
            )
            if len(slices[k]) == 0:
                writer.writerow(['(NONE)'])
            else:
                for item in slices[k]:
                    writer.writerow(
                        [
                            item['best_by_date_iso'],
                            item['quantity'],
                            item['brewery_name'],
                            item['beer_name'],
                            item['beer_type'],
                            '%.1f%%' % float(item['beer_abv']),
                            item['container'],
                        ]
                    )

    if styles_output:
        styles_writer = csv.writer(styles_output)
        styles_writer.writerow(['Styles'])
        for style_row in style_list:
            styles_writer.writerow([style_row['style'], style_row['count']])


def parse_cli_args() -> argparse.Namespace:
    """
    Set up & parse CLI arguments

    Returns:
        Namespace of parsed args
    """
    parser = argparse.ArgumentParser(
        description='Summarise expiry dates and types of beers on a list',
        usage=sys.argv[0] + ' SOURCE [--output OUTPUT] [--summary] [--help]'
    )
    parser.add_argument('source', help='Path to source file (export.json)')
    parser.add_argument('--summary', help='Generate a summary of styles rather than a full list', action='store_true')
    parser.add_argument('--output', required=False, help='Path to output file, STDOUT if not specified')
    args = parser.parse_args()
    return args


def run_cli():
    """
    Run as a cli script, according to arg setup
    """
    args = parse_cli_args()
    source = args.source
    dest = args.output
    if dest:
        output_handle = open(dest, 'w')
    else:
        output_handle = sys.stdout
    source_data = json.loads(file_contents(source))

    if args.summary:
        build_dated_stocklist(source_data, styles_output=output_handle)
    else:
        build_dated_stocklist(source_data, stocklist_output=output_handle)

    if dest:
        output_handle.close()


if __name__ == '__main__':
    run_cli()
