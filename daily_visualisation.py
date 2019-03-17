#!/usr/bin/env python3

import argparse
import json
import sys

from datetime import date, timedelta
from dateutil.parser import parse as parse_date
from imbibed import build_checkin_summaries
from math import ceil, floor
from svgwrite import Drawing
from typing import Tuple
from utils import file_contents

GRID_PITCH = 15
GRID_SQUARE = 10
GRID_BORDERS = {'top': 24, 'left': 52, 'bottom': 16, 'right': 10}
LEGEND_GRID = {'height': 50, 'left': 480, 'pitch': 32, 'cell_height': 22, 'cell_width': 28}

COLOR_LOW = (0xff, 0xff, 0xaa)
COLOR_HIGH = (0xaa, 0x22, 0x00)

CSS = """
    year { font-weight: bold; font-size: 14px }
    text { font-family: Verdana, Geneva, sans-serif; }
    text.year, text.month, text.day, text.legend_title { font-size: 12px; fill: #777 }
    text.month { text-anchor: middle }
    text.year, text.day { text-anchor: end }
    text.key { font-weight: bold; font-size: 14px; text-anchor: middle }
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
    left = grid_square_left(column, x_offset)
    top = grid_square_top(row, y_offset)
    return image.rect(insert=(left, top), size=(GRID_SQUARE, GRID_SQUARE), fill=fill)


def grid_square_top(row, y_offset=0):
    return GRID_BORDERS['top'] + (row - 1) * GRID_PITCH + y_offset


def grid_square_left(column, x_offset=0):
    return GRID_BORDERS['left'] + column * GRID_PITCH + x_offset


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


def build_daily_visualisation_image(daily_summary, measure, show_legend):
    years = set([parse_date(d).year for d in daily_summary])
    min_year = min(years)
    num_years = 1 + max(years) - min_year
    width, height_per_year = grid_size(7, 54)  # 52 weeks + ISO weeks 0, 53
    image_height = height_per_year * num_years + (LEGEND_GRID['height'] if show_legend else 0)
    image = init_image(width, image_height)

    for year in years:
        year_top = (height_per_year * (year - min_year))
        months = draw_year_labels(image, year, year_top)

        for month_index, month in enumerate(months):
            # Draw lines between months
            draw_month_boundary(image, month_index + 1, year, year_top)

    max_daily = ceil(max([daily_summary[d][measure] if measure in daily_summary[d] else 0 for d in daily_summary]))

    if measure == 'average':
        range_min = floor(min([daily_summary[d][measure] for d in daily_summary if measure in daily_summary[d]]))
    else:
        range_min = 0

    for date_string in daily_summary:
        daily_quantity = daily_summary[date_string][measure] if measure in daily_summary[date_string] else None
        day_date = parse_date(date_string)

        if daily_quantity is None:
            color = '#e0e0e0'
        else:
            color = fractional_fill_color((daily_quantity - range_min) / (max_daily - range_min))

        year = day_date.year
        offsets = (0, (year - min_year) * height_per_year)

        image.add(square_for_date(image, day_date, color, offsets))

    if show_legend:
        top = image_height - LEGEND_GRID['height']

        draw_legend(image, measure, top, max_daily, range_min)

    return image


def square_for_date(image, day_date, color, offsets):
    year, week, day = isocalendar_natural(day_date)

    day_square = square_in_grid(image, day, week, offsets=offsets, fill=color)
    return day_square


def draw_year_labels(image, year, year_top):
    months = 'JFMAMJJASOND'
    text_vrt_offset = 9
    image.add(
        image.text(
            '%d' % year,
            insert=(GRID_BORDERS['left'] - 8, year_top + GRID_BORDERS['top'] + text_vrt_offset - GRID_PITCH - 2),
            class_='year'
        )
    )
    image.add(
        image.text(
            'Mo',
            insert=(GRID_BORDERS['left'] - 8, year_top + GRID_BORDERS['top'] + text_vrt_offset),
            class_='day'
        )
    )
    image.add(
        image.text(
            'Su',
            insert=(GRID_BORDERS['left'] - 8, year_top + GRID_BORDERS['top'] + text_vrt_offset + 6 * GRID_PITCH),
            class_='day'
        )
    )
    # Draw month initials in line with first day of month
    for month_index, month in enumerate(months):
        start_location = month_start_location(month_index + 1, year, year_top)

        image.add(
            image.text(
                month,
                insert=(
                    offset_point(start_location, (GRID_PITCH + (GRID_SQUARE / 2), 0))[0],
                    year_top + GRID_BORDERS['top'] + text_vrt_offset - GRID_PITCH - 2
                ),
                class_='month'
            )
        )
    return months


def draw_month_boundary(image, month_number, year, year_top):
    start_location = month_start_location(month_number, year, year_top)
    end_location = offset_point(month_end_location(month_number, year, year_top), (0, GRID_PITCH))
    if date(year, month_number, 1) < date.today():
        half_pitch = (GRID_PITCH - GRID_SQUARE) / 2
        points = [
            (
                offset_point(start_location, (GRID_SQUARE + half_pitch, half_pitch))[0],
                grid_square_top(1, year_top) - half_pitch
            ),
            offset_point(start_location, (GRID_SQUARE + half_pitch, -half_pitch)),
            offset_point(start_location, (-half_pitch, -half_pitch)),
            (
                offset_point(start_location, (-half_pitch, -half_pitch))[0],
                grid_square_top(7, year_top) + GRID_SQUARE + half_pitch
            ),
            (
                offset_point(end_location, (-half_pitch, -half_pitch))[0],
                grid_square_top(7, year_top) + GRID_SQUARE + half_pitch
            ),
            offset_point(end_location, (-half_pitch, -half_pitch)),
            offset_point(end_location, (GRID_SQUARE + half_pitch, -half_pitch)),
            (
                offset_point(end_location, (GRID_SQUARE + half_pitch, half_pitch))[0],
                grid_square_top(1, year_top) - half_pitch
            ),
            (
                offset_point(start_location, (GRID_SQUARE + half_pitch, half_pitch))[0],
                grid_square_top(1, year_top) - half_pitch
            ),
        ]
        image.add(image.polyline(points, fill='#f4f4f4' if month_number % 2 else '#fff'))


def month_start_location(month, year, y_offset):
    """
    Return top-left position of grid square on first day of month

    Args:
        month:
        year:
        y_offset:

    Returns:

    """
    month_start_date = date(year, month, 1)
    return date_location(month_start_date, y_offset)


def month_end_location(month, year, y_offset):
    """
    Return top-left position of grid square on last day of month

    Args:
        month:
        year:
        y_offset:

    Returns:

    """
    if month == 12:
        next_month = 1
        next_month_year = year + 1
    else:
        next_month = month + 1
        next_month_year = year

    month_end_date = date(next_month_year, next_month, 1) - timedelta(days=1)
    return date_location(month_end_date, y_offset)


def date_location(when, y_offset) -> tuple:
    """
    Return top-left position of grid square on given day

    Args:
        when:
        y_offset:

    Returns:
        tuple of x,y position
    """
    year, week, day = isocalendar_natural(when)
    return grid_square_left(week), grid_square_top(day, y_offset)


def isocalendar_natural(when):
    """
    Isocalendar week number without crossing month boundaries

    Args:
        when:

    Returns:

    """
    real_year = when.year
    (iso_year, week, day) = when.isocalendar()
    if iso_year > real_year:
        week = 53
    elif iso_year < real_year:
        week = 0

    return real_year, week, day


def offset_point(point: tuple, by: tuple) -> tuple:
    return point[0] + by[0], point[1] + by[1]


def draw_legend(image: Drawing, measure: str, top: int, range_max: float, range_min: int = 0):
    # Generate up to 5 integer steps
    step = int(ceil((range_max - range_min) / 5))

    image.add(
        image.text(
            'Daily %s: ' % measure,
            insert=(LEGEND_GRID['left'], top + 3 * LEGEND_GRID['cell_height'] / 4),
            class_='legend_title'
        )
    )
    steps = list(range(range_min, int(range_max + 1), step))
    if max(steps) != int(range_max):
        steps.append(int(range_max))

    for offset, marker in enumerate(steps):
        left = LEGEND_GRID['left'] + offset * LEGEND_GRID['pitch']
        image.add(
            image.rect(
                (left, top),
                (LEGEND_GRID['cell_width'], LEGEND_GRID['cell_height']),
                fill=fractional_fill_color((marker - range_min) / (range_max - range_min))
            )
        )
        image.add(
            image.text(
                marker,
                insert=(left + LEGEND_GRID['cell_width'] / 2, top + 3 * LEGEND_GRID['cell_height'] / 4),
                class_='key',
                fill='#ffffff' if marker > range_max / 2 else '#000000'
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
    group.add_argument('--units', help='Show number of units (default)', action='store_true')
    group.add_argument('--drinks', help='Show number of drinks', action='store_true')
    group.add_argument('--average', help='Show average score)', action='store_true')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    run_cli()
