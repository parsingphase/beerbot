#!/usr/bin/env python3
"""
Analyze stock data. Run from cli with --help for details.
"""
import argparse
import json
import sys
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Dict, List, Optional, TextIO, Union
from urllib.parse import quote as quote_url

from dateutil.relativedelta import relativedelta

from bot_version import version
from utils import build_csv_from_list, file_contents


class TaggedText(ABC):
    """
    Abstract class for data that can act as string or html
    """

    @abstractmethod
    def to_string(self) -> str:
        """
        Return string representation of the data
        """

    @abstractmethod
    def to_html(self) -> str:
        """
        Return html representation of the data
        """

    def __str__(self) -> str:
        """
        Return string representation of the data by casting
        """
        return self.to_string()


class LinkedText(TaggedText):
    """
    Tagged data that can display as <a href> link or plain text
    """

    def __init__(self, text: str, url: str):
        self.text = text
        self.url = url

    def to_string(self) -> str:
        return self.text

    def to_html(self) -> str:
        return f'<a href="{self.url}">{self.text}</a>' if self.url else self.text


def generate_stocklist_files(source_data: list, stocklist_output: TextIO = None,
                             styles_output: TextIO = None) -> None:
    """
    Convert the parsed JSON from a list feed into a CSV reporting stock levels and expiry

    Args:
        source_data: json data parsed into a list
        stocklist_output: buffer to write stock list to
        styles_output: buffer to write styles summary to
    """
    stocklist = [] if stocklist_output else None  # type: Optional[List]
    style_summary = [] if styles_output else None  # type: Optional[List]

    build_stocklists(source_data, stocklist=stocklist, style_summary=style_summary)

    if stocklist_output and stocklist is not None:
        build_csv_from_list(stocklist, stocklist_output)

    if styles_output and style_summary is not None:
        build_csv_from_list(style_summary, styles_output)


def build_stocklists(source_data: list, stocklist: list = None, style_summary: list = None) -> None:
    """
    Assemble JSON data from stock list export into lists for subsequent writing to selected file format

    Args:
        source_data: Source data unpacked from JSON
        stocklist:
        style_summary:

    Returns:

    """
    # pylint: disable=R0912,R0914
    thresholds = [
        {'description': 'Undated beers', 'ends': '0000-00-00'},
        {'description': 'Expired beers', 'ends': date.today().strftime('%Y-%m-%d')},
        {'description': 'Within one month', 'ends': (date.today() + relativedelta(months=+1)).strftime('%Y-%m-%d')},
        {'description': 'Within two months', 'ends': (date.today() + relativedelta(months=+2)).strftime('%Y-%m-%d')},
        {'description': 'More than two months away'}
    ]
    expiry_sets = [{} for _ in range(len(thresholds))]  # type: List[Dict]
    styles = {}  # type: Dict
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

    if stocklist is not None:

        stocklist.append(['Expiry', 'Type', '#', 'Brewery', 'Beverage', 'Subtype', 'ABV', 'Serving', 'BBE'])
        for k, expiry_set in enumerate(expiry_sets):
            if expiry_sets[k]:
                distinct_beer_count = sum([sum([1 for _ in expiry_set[style]]) for style in expiry_set])
                if list_has_quantities:
                    quantity = sum([sum([int(d['quantity']) for d in expiry_set[style]]) for style in expiry_set])
                    stocklist.append(
                        [
                            '%s: %d %s of %d %s' % (
                                thresholds[k]['description'],
                                quantity,
                                plural('item', quantity),
                                distinct_beer_count,
                                plural('beer', distinct_beer_count),
                            )
                        ]
                    )
                else:
                    stocklist.append(
                        [
                            '%s: %d %s' % (
                                thresholds[k]['description'],
                                distinct_beer_count,
                                plural('beer', distinct_beer_count),
                            )
                        ]
                    )

                # Sort styles by name
                for style in sorted(expiry_sets[k]):
                    first = True
                    drinks = expiry_sets[k][style]
                    drinks.sort(key=lambda d: (d['brewery_name'], d['beer_name']))
                    for item in drinks:
                        bbd = item.get('best_by_date_iso', '')
                        url = 'https://untappd.com/search?q='
                        url = url + quote_url(item["brewery_name"] + ' ' + item["beer_name"])
                        stocklist.append(
                            [
                                '',
                                style if first else '',
                                item.get('quantity', ''),
                                item['brewery_name'],
                                LinkedText(item['beer_name'], url),
                                item['beer_type'],
                                '%.1f%%' % float(item['beer_abv']),
                                item.get('container', ''),
                                bbd if bbd != '0000-00-00' else '',
                            ]
                        )
                        first = False

                if len(expiry_sets) > k + 1:
                    stocklist.append([''])  # space before next

        if list_has_quantities:
            stocklist.append(
                [
                    'TOTAL: %d items of %d beers' % (
                        sum([int(item['quantity']) for item in source_data]),
                        len(source_data)
                    )
                ]
            )

    if style_summary is not None:
        style_list = []
        for style, style_count in styles.items():
            style_list.append({'style': style, 'count': style_count})
        style_list.sort(key=lambda b: (0 if b['count'] is None else (0 - b['count']), b['style']))
        style_summary.append(['Styles'])
        for style_row in style_list:
            style_summary.append(
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
        usage=sys.argv[0] + ' SOURCE [--output OUTPUT] [--summary|--html] [--help]'
    )
    parser.add_argument('source', help='Path to source file (export.json)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--html', help='Export stocklist as html instead of csv', action='store_true')
    group.add_argument('--summary', help='Generate a summary of styles rather than a full list', action='store_true')
    parser.add_argument('--output', required=False, help='Path to output file, STDOUT if not specified')
    args = parser.parse_args()
    return args


def build_html_from_list(stocklist: List[list], stocklist_output: TextIO, title: str = None):
    """
    Create HTML table from Stocklist

    Args:
        title: Optional title
        stocklist: Summarised data
        stocklist_output: Buffer for HTML output

    Returns:

    """

    def wrap(contents: Union[str, TaggedText], tag: str):
        contents = contents.to_html() if isinstance(contents, TaggedText) else contents
        return '<%s>%s</%s>' % (tag, contents, tag)

    date_format = '%B %-d %Y'
    # date_format += ' %X'
    today = datetime.now().strftime(date_format)

    if title is None:
        title = "Stocklist"
        list_name = "List"
    else:
        list_name = title

    print({'build_html_from_list': {'title': title}})

    stocklist_output.write(
        """<html><head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
        <title>%s</title>
        <style type="text/css" media="all">
            body { font-family: "Helvetica Neue", "Helvetica", sans-serif; }
            div.container { padding: 20px 40px; }
            @media only screen and (max-device-width : 1024px) {
                div.container { padding: 4px; }
            }
            h1 { text-align: right; padding-right: 40px; font-size: 1.2em; margin-top: 0}
            table { border-collapse: collapse; border: 1px solid #ddd; min-width: 85em}
            th { background-color: #eee; text-align: left; padding: 6px }
            tr:first-child th {background-color: #ddd;}
            td { text-align: left; padding: 2 6px; border-top: 1px solid #ddd; border-bottom: 1px solid #ddd; }
            a, a:link { color: #000; text-decoration: none }
            p.attribution { text-align: right; padding-right: 40px }
        </style>
        </head>
        <body>
            <div class="container">
            <h1>%s generated %s by <a href="https://beerbot.phase.org">Beerbot</a></h1>
            <table>
            """ % (title, list_name, today)
    )

    first = True
    for row in stocklist:
        if not ''.join([str(i) for i in row]):  # If anything in line
            continue

        if len(row) == 1:
            row_string = '<tr><th colspan="9">%s</th></tr>\n' % row[0]
        elif first:
            row_string = ''.join(map(lambda x: wrap(x, 'th'), row))
            row_string = wrap(row_string, 'tr') + '\n'
        else:
            row[-1] = row[-1].replace('-', '\u2011')  # Replace hyphens in best-before with non-breaking
            row_string = wrap(row[0], 'th')
            row_string += ''.join(map(lambda x: wrap(x, 'td'), row[1:]))
            row_string = wrap(row_string, 'tr') + '\n'

        stocklist_output.write(row_string)

        first = False

    stocklist_output.write(
        """</table> &nbsp;
            <p class="attribution">Built by %s</p>
                </div>
            </body>
        </html>""" % ('development version' if version == 'development' else version)
    )


def plural(noun: str, quantity: int) -> str:
    """
    Naive plural: return noun suffixed by 's' if quantity is not 1
    Args:
        noun:
        quantity:

    Returns:
        str
    """
    return noun + ('' if quantity == 1 else 's')


def run_cli():
    """
    Run as a cli script, according to arg setup
    """
    args = parse_cli_args()
    source = args.source
    dest = args.output
    if dest:
        # R1732 wants a 'with' here. Can't do that neatly with 2 potential opens
        output_handle = open(dest, 'w')  # pylint: disable=consider-using-with
    else:
        output_handle = sys.stdout

    source_data = json.loads(file_contents(source))

    if args.summary:
        generate_stocklist_files(source_data, styles_output=output_handle)
    elif args.html:
        stocklist = []
        build_stocklists(source_data, stocklist=stocklist)
        build_html_from_list(stocklist, stocklist_output=output_handle)
    else:
        generate_stocklist_files(source_data, stocklist_output=output_handle)

    if dest:
        output_handle.close()


if __name__ == '__main__':
    run_cli()
