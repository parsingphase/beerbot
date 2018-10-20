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
    thresholds = [
        {'description': 'Undated beers', 'ends': '0000-00-00'},
        {'description': 'Expired beers', 'ends': date.today().strftime('%Y-%m-%d')},
        {'description': 'Within one month', 'ends': (date.today() + relativedelta(months=+1)).strftime('%Y-%m-%d')},
        {'description': 'Within two months', 'ends': (date.today() + relativedelta(months=+2)).strftime('%Y-%m-%d')},
        {'description': 'More than two months away'}
    ]
    expiry_sets = [{} for _ in range(len(thresholds))]
    styles = {}
    list_has_quantities = False

    for item in source_data:
        style = item['beer_type'].split(' -')[0].strip()

        if 'quantity' in item:
            if style not in styles:
                styles[style] = 0
            styles[style] += int(item['quantity'])
            list_has_quantities = True
        else:
            if style not in styles:
                styles[style] = None

        # Strictly only needed for full stocklist
        due = item.get('best_by_date_iso', '0000-00-00')
        for idx, threshold in enumerate(thresholds):
            if 'ends' in threshold and due <= threshold['ends']:
                if style not in expiry_sets[idx]:
                    expiry_sets[idx][style] = []
                expiry_sets[idx][style].append(item)
                break

            if 'ends' not in threshold:
                if style not in expiry_sets[idx]:
                    expiry_sets[idx][style] = []
                expiry_sets[idx][style].append(item)

    if stocklist_output:
        writer = csv.writer(stocklist_output)
        writer.writerow(['Expiry', 'Type', '#', 'Brewery', 'Beverage', 'Subtype', 'ABV', 'Serving', 'BBE'])
        for k, expiry_set in enumerate(expiry_sets):
            if len(expiry_sets[k]):
                if list_has_quantities:
                    writer.writerow(
                        [
                            '%s: %d item(s) of %d beer(s)' % (
                                thresholds[k]['description'],
                                sum([sum([int(d['quantity']) for d in expiry_set[style]]) for style in expiry_set]),
                                len(expiry_set),
                            )
                        ]
                    )
                else:
                    writer.writerow(
                        [
                            '%s: %d beer(s)' % (
                                thresholds[k]['description'],
                                len(expiry_set),
                            )
                        ]
                    )

                # Sort styles by name
                for style in sorted(expiry_sets[k]):
                    first = True
                    drinks = expiry_sets[k][style]
                    drinks.sort(key=lambda d: (d['brewery_name'], d['beer_name']))
                    for item in drinks:
                        writer.writerow(
                            [
                                '',
                                style if first else '',
                                item.get('quantity', ''),
                                item['brewery_name'],
                                item['beer_name'],
                                item['beer_type'],
                                '%.1f%%' % float(item['beer_abv']),
                                item.get('container', ''),
                                item.get('best_by_date_iso', ''),
                            ]
                        )
                        first = False

                if len(expiry_sets) > k + 1:
                    writer.writerow([''])  # space before next

    if styles_output:
        style_list = []
        for style in styles:
            style_list.append({'style': style, 'count': styles[style]})
        style_list.sort(key=lambda b: (0 if b['count'] is None else (0 - b['count']), b['style']))
        styles_writer = csv.writer(styles_output)
        styles_writer.writerow(['Styles'])
        for style_row in style_list:
            styles_writer.writerow(
                [style_row['style']] if style_row['count'] is None else [style_row['style'], style_row['count']]
            )


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
