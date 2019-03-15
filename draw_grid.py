#!/usr/bin/env python3

import argparse
import json
import sys

from dateutil.parser import parse as parse_date
from imbibed import build_checkin_summaries
from svgwrite import Drawing
from typing import Tuple
from utils import file_contents

GRID_PITCH = 13
GRID_SQUARE = 10
GRID_BORDERS = {'top': 15, 'left': 40, 'bottom': 5, 'right': 5}

COLOR_LOW = (0xff, 0xff, 0xcc)
COLOR_HIGH = (0x99, 0x22, 0x00)


def grid_size(rows: int, columns: int) -> Tuple[int, int]:
    width = GRID_BORDERS['left'] + GRID_PITCH * (columns - 1) + GRID_SQUARE + GRID_BORDERS['right']
    height = GRID_BORDERS['top'] + GRID_PITCH * (rows - 1) + GRID_SQUARE + GRID_BORDERS['bottom']
    return width, height


# SVG puts 0,0 at top left
def square_at(image: Drawing, row: int, column: int, fill='#ffdd00'):
    left = GRID_BORDERS['left'] + (column - 1) * GRID_PITCH
    top = GRID_BORDERS['top'] + (row - 1) * GRID_PITCH
    return image.rect(insert=(left, top), size=(GRID_SQUARE, GRID_SQUARE), fill=fill)


def fractional_fill_color(fraction: float) -> str:
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

    daily_summary = {}
    build_checkin_summaries(source_data, daily_summary)

    image = create_grid_image()

    max_daily = max([daily_summary[d]['units'] for d in daily_summary])

    for date_string in daily_summary:
        units = daily_summary[date_string]['units']
        date = parse_date(date_string)
        (year, week, day) = date.isocalendar()
        color = fractional_fill_color(units / max_daily) if units else '#eeeeee'
        image.add(square_at(image, day, week, fill=color))

    if dest:
        image.saveas(dest)
    else:
        raise Exception('dest required')


def create_grid_image() -> Drawing:
    width, height = grid_size(7, 52)
    # print('%d by %d grid => %d x %d pixels' % (columns, rows, width, height))
    image = Drawing(size=('%dpx' % width, '%dpx' % height))
    image.add(image.rect((0, 0), (width, height), fill='white'))
    return image


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='Visualise consumption of alcoholic drinks from an Untappd JSON export file',
        usage=sys.argv[0] + ' SOURCE [--output OUTPUT]',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('source', help='Path to source file (export.json)')
    parser.add_argument('--output', required=False, help='Path to output file, STDOUT if not specified')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    run_cli()
