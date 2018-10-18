#!/usr/bin/env python

import argparse
import csv
import sys
import json
import matplotlib.pyplot as plt
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


def build_dated_list_summary(source_data: list, output_handle: TextIO) -> None:
    """
    Convert the parsed JSON from a list feed into a CSV reporting stock levels and expiry

    Args:
        source_data: json data parsed into a list
        output_handle: filehandle to write to

    """
    source_data.sort(key=lambda b: b['best_by_date_iso'])
    thresholds = {
        'undated': {'description': 'Undated beers', 'ends': '0000-00-00'},
        'now': {'description': 'Expired beers', 'ends': date.today().strftime('%Y-%m-%d')},
        'month': {'description': 'Within one month',
                  'ends': (date.today() + relativedelta(months=+1)).strftime('%Y-%m-%d')},
        'two': {'description': 'Within two months',
                'ends': (date.today() + relativedelta(months=+2)).strftime('%Y-%m-%d')},
        'future': {'description': 'More than two months away'}
    }
    slices = {'undated': [], 'now': [], 'month': [], 'two': [], 'future': []}
    styles = {}
    for item in source_data:
        style = item['beer_type'].split(' -')[0].strip()
        if not style in styles:
            styles[style] = 0
        styles[style] += int(item['quantity'])

        due = item['best_by_date_iso']
        if due <= thresholds['undated']['ends']:
            slices['undated'].append(item)
        elif due < thresholds['now']['ends']:
            slices['now'].append(item)
        elif due < thresholds['month']['ends']:
            slices['month'].append(item)
        elif due < thresholds['two']['ends']:
            slices['two'].append(item)
        else:
            slices['future'].append(item)

    style_list = []
    for style in styles:
        style_list.append({'style': style, 'count': styles[style]})
    style_list.sort(key=lambda b: (0 - b['count'], b['style']))

    writer = csv.writer(output_handle)
    for k in slices:
        writer.writerow(
            [
                '%s: %d item(s) of %d beer(s)' % (
                    thresholds[k]['description'], sum([int(s['quantity']) for s in slices[k]]), len(slices[k]),
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

    for i in range(5):
        writer.writerow([''])

    writer.writerow(['Styles'])
    for style_row in style_list:
        writer.writerow([style_row['style'], style_row['count']])

    pie_file = 'tmp/styles.png'
    plot_styles_pie(style_list, pie_file)


def plot_styles_pie(style_list: list, pie_file: str):
    plot_values = []
    plot_keys = []
    for style_row in style_list:
        plot_keys.append(style_row['style'])
        plot_values.append(style_row['count'])
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    wedges, texts = ax1.pie(plot_values, startangle=180, counterclock=False)
    ax1.axis('equal')

    ax1.legend(wedges, plot_keys,
               title="Styles",
               loc="center left",
               bbox_to_anchor=(1, 0, 0.5, 1))

    plt.subplots_adjust(left=0.02, bottom=0.1, right=0.6)

    plt.savefig(pie_file)


def parse_cli_args() -> argparse.Namespace:
    """
    Set up & parse CLI arguments

    Returns:
        Namespace of parsed args
    """
    parser = argparse.ArgumentParser(
        description='Summarise expiry dates and types of beers on a list',
        usage=sys.argv[0] + ' SOURCE [--output OUTPUT] [--help]'
    )
    parser.add_argument('source', help='Path to source file (export.json)')
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
    build_dated_list_summary(source_data, output_handle)

    if dest:
        output_handle.close()


if __name__ == '__main__':
    run_cli()
