#!/usr/bin/env python3


import svgwrite
from typing import Tuple

GRID_PITCH = 13
GRID_SQUARE = 10
GRID_BORDERS = {'top': 15, 'left': 40, 'bottom': 5, 'right': 5}

COLOR_LOW = (0xff, 0xff, 0xcc)
COLOR_HIGH = (0xbb, 0x55, 0x00)


def grid_size(rows: int, columns: int) -> Tuple[int, int]:
    width = GRID_BORDERS['left'] + GRID_PITCH * (columns - 1) + GRID_SQUARE + GRID_BORDERS['right']
    height = GRID_BORDERS['top'] + GRID_PITCH * (rows - 1) + GRID_SQUARE + GRID_BORDERS['bottom']
    return width, height


# SVG put 0,0 at top left
def square_at(image: svgwrite.Drawing, row: int, column: int, fill='#ffdd00'):
    left = GRID_BORDERS['left'] + (column - 1) * GRID_PITCH
    top = GRID_BORDERS['top'] + (row - 1) * GRID_PITCH
    return image.rect(insert=(left, top), size=(GRID_SQUARE, GRID_SQUARE), fill=fill)


def fractional_fill_color(fraction: float) -> str:
    color = []
    for k in range(0, 3):
        color.append(COLOR_LOW[k] + int(fraction * (COLOR_HIGH[k] - COLOR_LOW[k])))

    # print(color)

    color_string = '#' + (''.join(map(lambda c: "%02x" % c, color)))

    return color_string


def run_cli():
    rows = 7
    columns = 52
    width, height = grid_size(rows, columns)
    print('%d by %d grid => %d x %d pixels' % (columns, rows, width, height))

    image = svgwrite.Drawing(size=('%dpx' % width, '%dpx' % height))
    image.add(image.rect((0, 0), (width, height), fill='white'))

    for r in range(1, rows + 1):
        for c in range(1, columns + 1):
            image.add(square_at(image, r, c, fill=fractional_fill_color((r + c) / (rows + columns))))

    image.saveas('tmp/grid.svg')


if __name__ == '__main__':
    run_cli()
