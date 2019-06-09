#!/usr/bin/env python3

import argparse
import json
import sys

from svg_calendar import draw_daily_count_image
from imbibed import build_checkin_summaries
from math import floor
from utils import file_contents, filter_source_data


def run_cli():
    args = parse_cli_args()
    source = args.source
    dest = args.output
    source_data = json.loads(file_contents(source))
    show_legend = args.legend

    filter_strings = args.filter
    if filter_strings:
        source_data = filter_source_data(filter_strings, source_data)
        if not source_data:
            raise Exception('Your filter left no data to analyse')

    daily_summary = {}
    build_checkin_summaries(source_data, daily_summary)

    if args.drinks:
        measure = 'drinks'
    elif args.average:
        measure = 'average'
    else:
        measure = 'units'

    image = build_daily_visualisation_image(daily_summary, measure, show_legend)

    if dest:
        image.saveas(dest, pretty=True)
    else:
        image.write(sys.stdout, pretty=True)


def build_daily_visualisation_image(daily_summary: dict, measure: str, show_legend: bool):
    """
    Build a github-style calendar view of the given measuer

    Args:
        daily_summary:
        measure:
        show_legend:

    Returns:

    """
    daily_count = {d: daily_summary[d][measure] for d in daily_summary if measure in daily_summary[d]}
    if measure == 'average':
        range_min = floor(min([daily_summary[d][measure] for d in daily_summary if measure in daily_summary[d]]))
    else:
        range_min = 0
    return draw_daily_count_image(daily_count, show_legend, f'Daily {measure}', range_min)


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='Visualise consumption of alcoholic drinks from an Untappd JSON export file',
        usage=sys.argv[0] + ' SOURCE [--output OUTPUT] [--drinks|--units] [--legend] [--filter=…] [--help]',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=('Filter is based on JSON input keys.\nExample usages:\n'
                '    "--filter=venue_name=The Red Lion"\n    "--filter=created_at>2017-10-01"'
                )
    )
    parser.add_argument('source', help='Path to source file (export.json)')
    parser.add_argument('--output', required=False, help='Path to output file, STDOUT if not specified')
    parser.add_argument('--legend', required=False, help='Add a legend to image', action='store_true')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--units', help='Show number of units (default)', action='store_true')
    group.add_argument('--drinks', help='Show number of drinks', action='store_true')
    group.add_argument('--average', help='Show average score)', action='store_true')

    parser.add_argument('--filter',
                        metavar='RULE',
                        help='Filter input list by rule',
                        action='append')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    run_cli()
