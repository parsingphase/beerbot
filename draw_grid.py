#!/usr/bin/env python3

import argparse
import json
import sys

from datetime import date
from dateutil.parser import parse as parse_date
from imbibed import build_checkin_summaries
from math import ceil
from svgwrite import Drawing
from typing import Tuple
from utils import file_contents

GRID_PITCH = 13
GRID_SQUARE = 10
GRID_BORDERS = {'top': 24, 'left': 52, 'bottom': 16, 'right': 5}
LEGEND_GRID = {'height': 50, 'left': 480, 'pitch': 32, 'cell_height': 22, 'cell_width': 28}

COLOR_LOW = (0xff, 0xff, 0xcc)
COLOR_HIGH = (0x99, 0x22, 0x00)

CSS = """
    year {font-weight: bold; font-size: 14px}
    text { font-family: Verdana, Geneva, sans-serif; }
    text.year, text.month, text.day, text.legend_title { font-size: 12px; fill: #777}
    text.key {font-weight: bold; font-size: 14px; text-anchor: middle }
    text.legend_title {font-weight: bold; font-size: 14px; text-anchor: end }
"""


def grid_size(rows: int, columns: int) -> Tuple[int, int]:
    width = GRID_BORDERS['left'] + GRID_PITCH * (columns - 1) + GRID_SQUARE + GRID_BORDERS['right']
    height = GRID_BORDERS['top'] + GRID_PITCH * (rows - 1) + GRID_SQUARE + GRID_BORDERS['bottom']
    return width, height


# SVG puts 0,0 at top left
def square_in_grid(image: Drawing, row: int, column: int, offsets=(), fill='#ffdd00'):
    x_offset = offsets[0] if len(offsets) else 0
    y_offset = offsets[1] if len(offsets) > 1 else 0
    left = GRID_BORDERS['left'] + (column - 1) * GRID_PITCH + x_offset
    top = GRID_BORDERS['top'] + (row - 1) * GRID_PITCH + y_offset
    return image.rect(insert=(left, top), size=(GRID_SQUARE, GRID_SQUARE), fill=fill)


def fractional_fill_color(fraction: float) -> str:
    """
    Get a hex-triple color between our two configured limits
    Args:
        fraction: 0-1 value of position between limits

    Returns:

    """
    color = []
    for k in range(0, 3):
        color.append(COLOR_LOW[k] + int(fraction * (COLOR_HIGH[k] - COLOR_LOW[k])))

    color_string = '#' + (''.join(map(lambda c: "%02x" % c, color)))

    return color_string


def run_cli():
    args = parse_cli_args()
    source = args.source
    dest = args.output
    source_data = json.loads(file_contents(source))
    show_legend = args.legend
    daily_summary = {}
    build_checkin_summaries(source_data, daily_summary)

    measure = 'drinks' if args.drinks else 'units'

    image = build_daily_visualisation_image(daily_summary, measure, show_legend)

    if dest:
        image.saveas(dest, pretty=True)
    else:
        image.write(sys.stdout, pretty=True)


def build_daily_visualisation_image(daily_summary, measure, show_legend):
    years = set([parse_date(d).year for d in daily_summary])
    min_year = min(years)
    num_years = 1 + max(years) - min_year
    width, height_per_year = grid_size(7, 53)
    image_height = height_per_year * num_years + LEGEND_GRID['height'] if show_legend else 0
    image = init_image(width, image_height)
    text_vrt_offset = 9
    months = 'JFMAMJJASOND'
    for year in years:
        year_top = (height_per_year * (year - min_year))
        image.add(
            image.text(
                '%d' % year,
                insert=(GRID_BORDERS['left'] - 46, year_top + GRID_BORDERS['top'] + text_vrt_offset - GRID_PITCH - 2),
                class_='year'
            )
        )
        image.add(
            image.text(
                'Mo',
                insert=(GRID_BORDERS['left'] - 24, year_top + GRID_BORDERS['top'] + text_vrt_offset),
                class_='day'
            )
        )
        image.add(
            image.text(
                'Su',
                insert=(GRID_BORDERS['left'] - 24, year_top + GRID_BORDERS['top'] + text_vrt_offset + 6 * GRID_PITCH),
                class_='day'
            )
        )

        # Draw month initials in line with first day of month
        for num, month in enumerate(months):
            month_start_date = date(year, num + 1, 1)
            (week_year, week, _) = month_start_date.isocalendar()
            week = 1 if num == 0 and year != week_year else week  # If Jan 1 not in this isoyear, shift it to 1st week
            image.add(
                image.text(
                    month,
                    insert=(
                        GRID_BORDERS['left'] + GRID_PITCH * (week - 1),
                        year_top + GRID_BORDERS['top'] + text_vrt_offset - GRID_PITCH - 2
                    ),
                    class_='month'
                )
            )
    max_daily = ceil(max([daily_summary[d][measure] for d in daily_summary]))

    for date_string in daily_summary:
        daily_quantity = daily_summary[date_string][measure]
        day_date = parse_date(date_string)
        (year, week, day) = day_date.isocalendar()
        color = fractional_fill_color(daily_quantity / max_daily) if daily_quantity else '#eeeeee'
        offsets = (0, (year - min_year) * height_per_year)
        image.add(square_in_grid(image, day, week, offsets=offsets, fill=color))
    if show_legend:
        top = image_height - LEGEND_GRID['height']
        draw_legend(image, measure, max_daily, top)
    return image


def draw_legend(image: Drawing, measure: str, max_value: float, top: int):
    # Generate up to 5 integer steps
    step = int(ceil(max_value / 5))

    image.add(
        image.text(
            'Daily %s: ' % measure,
            insert=(LEGEND_GRID['left'], top + 3 * LEGEND_GRID['cell_height'] / 4),
            class_='legend_title'
        )
    )
    steps = list(range(0, int(max_value + 1), step))
    if max(steps) != int(max_value):
        steps.append(int(max_value))

    for offset, marker in enumerate(steps):
        left = LEGEND_GRID['left'] + offset * LEGEND_GRID['pitch']
        image.add(
            image.rect(
                (left, top),
                (LEGEND_GRID['cell_width'], LEGEND_GRID['cell_height']),
                fill=fractional_fill_color(marker / max_value)
            )
        )
        image.add(
            image.text(
                marker,
                insert=(left + LEGEND_GRID['cell_width'] / 2, top + 3 * LEGEND_GRID['cell_height'] / 4),
                class_='key',
                fill='#ffffff' if marker > max_value / 2 else '#000000'
            )
        )


def init_image(width: int, height: int) -> Drawing:
    image = Drawing(size=('%dpx' % width, '%dpx' % height))
    image.add(image.rect((0, 0), (width, height), fill='white'))
    image.defs.add(image.style(CSS))
    return image


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='Visualise consumption of alcoholic drinks from an Untappd JSON export file',
        usage=sys.argv[0] + ' SOURCE [--output OUTPUT] [--drinks|--units] [--legend]',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('source', help='Path to source file (export.json)')
    parser.add_argument('--output', required=False, help='Path to output file, STDOUT if not specified')
    parser.add_argument('--legend', required=False, help='Add a legend to image', action='store_true')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--drinks', help='Show number of drinks', action='store_true')
    group.add_argument('--units', help='Show number of units (default)', action='store_true')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    run_cli()
