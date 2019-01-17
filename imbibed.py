#!/usr/bin/env python

import argparse
import csv
import re
import sys
import json
from typing import Optional
from datetime import timedelta
from dateutil.parser import parse as parse_date  # pipenv install  python-dateutil
from typing import TextIO
from utils import file_contents

DEFAULT_UNIT = 'pint'
DEFAULT_SERVING_SIZES = {'draft': 568 / 2, 'cask': 568 / 2, 'taster': 150, 'bottle': 330, 'can': 330}
MAX_VALID_MEASURE = 2500  # For detection of valid inputs. More than a yard of ale or a Maß


def parse_measure(measure_string: str) -> int:
    """
    Read a measure as recorded in the comment field and parse it into a number of millilitres
    Args:
        measure_string: String as found in square brackets

    Returns:
        Integer number of ml
    """
    divisors = {'quarter': 4, 'third': 3, 'half': 2}
    divisor_match = '(?P<divisor_text>' + '|'.join(divisors.keys()) + ')'
    units = {'ml': 1, 'cl': 10, 'litre': 1000, 'liter': 1000, 'pint': 568, 'sip': 25, 'taste': 25}
    unit_match = '(?P<unit>' + '|'.join(units.keys()) + ')s?'  # allow plurals
    optional_unit_match = '(' + unit_match + ')?'
    fraction_match = '(?P<fraction>\d+/\d+)'
    quantity_match = '(?P<quantity>\d+)'
    optional_space = '\s*'
    candidate_matches = [
        '^' + unit_match + '$',
        '^' + quantity_match + optional_space + optional_unit_match + '$',
        '^' + divisor_match + optional_space + optional_unit_match + '$',
        '^' + fraction_match + optional_space + optional_unit_match + '$',
    ]

    match = None
    quantity = None

    for pattern in candidate_matches:
        match = re.match(pattern, measure_string)
        if match:
            break

    if match:
        match_dict = match.groupdict()
        unit = match_dict['unit'] if 'unit' in match_dict and match_dict['unit'] is not None else DEFAULT_UNIT
        quantity = units[unit]
        if 'quantity' in match_dict:
            quantity *= int(match_dict['quantity'])
        elif 'divisor_text' in match_dict:
            quantity /= divisors[match_dict['divisor_text']]
        elif 'fraction' in match_dict:
            fraction_parts = [int(s) for s in match_dict['fraction'].split('/')]
            quantity = quantity * fraction_parts[0] / fraction_parts[1]

    if quantity > MAX_VALID_MEASURE:
        raise Exception('Measure of [%s] appears to be invalid. Did you miss out a unit?' % measure_string)

    return int(quantity)


def measure_from_comment(comment: str) -> Optional[int]:
    """
    Extract any mention of a measure (in square brackets) from the comment string on a checkin, and parse it

    Args:
        comment: Checking comment field

    Returns:
        int measure in ml
    """
    measure_match = re.search(r'\[([^\[\]]+)\]', comment)  # evil thing to match!
    match_string = measure_match[1] if measure_match else None
    if match_string:
        drink_measure = parse_measure(match_string)
    else:
        drink_measure = None
    return drink_measure


def measure_from_serving(serving: str) -> Optional[int]:
    """
    Get a default measure size from the serving style, if possible
    Args:
        serving: One of the Untappd serving names

    Returns:
        int measure in ml
    """
    serving = serving.lower()
    defaults = DEFAULT_SERVING_SIZES
    drink_measure = defaults[serving] if serving in defaults else None
    return drink_measure


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='Analyse consumption of alcoholic drinks from an Untappd JSON export file',
        usage=sys.argv[0] + ' SOURCE [--output OUTPUT] [--weekly|--daily|--style|--brewery] [--help]'
    )
    parser.add_argument('source', help='Path to source file (export.json)')
    parser.add_argument('--output', required=False, help='Path to output file, STDOUT if not specified')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--daily', help='Summarise checkins by day', action='store_true')
    group.add_argument('--weekly', help='Summarise checkins by week', action='store_true')
    group.add_argument('--style', help='Summarise styles of drinks checked in', action='store_true')
    group.add_argument('--brewery', help='Summarise checkins by brewery', action='store_true')

    args = parser.parse_args()
    return args


def analyze_checkins(
        source_data: list,
        daily_output: TextIO = None,
        weekly_output: TextIO = None,
        styles_output: TextIO = None,
        brewery_output: TextIO = None,
):
    """
    Build a summary of intake from the exported data, and save to buffer
    Args:
        source_data:
        daily_output:
        weekly_output:
        styles_output:
        brewery_output:

    Returns:

    """
    daily = {}
    styles = {}
    breweries = {}
    for checkin in source_data:
        # fields of interest: comment, created_at, beer_abv, serving_type
        abv = float(checkin['beer_abv'])
        created_at = parse_date(checkin['created_at'])  # <class 'datetime.datetime'>
        date_key = created_at.date().isoformat()

        if date_key not in daily:
            daily[date_key] = {
                'drinks': 0,
                'units': 0,
                'alcohol_ml': 0,
                'beverage_ml': 0,
                'estimated': '',
                'rated': 0,
                'total_score': 0.0,
            }

        daily[date_key]['drinks'] += 1
        if checkin['rating_score']:
            daily[date_key]['rated'] += 1
            daily[date_key]['total_score'] += float(checkin['rating_score'])

        measure = measure_from_comment(checkin['comment'])
        if measure is None:
            measure = measure_from_serving(checkin['serving_type'])
            daily[date_key]['estimated'] = '*'

        if measure:
            daily[date_key]['beverage_ml'] += measure
            if abv:
                alcohol_volume = float(measure) * abv / 100
                daily[date_key]['alcohol_ml'] += alcohol_volume
                daily[date_key]['units'] += alcohol_volume / 10

        else:
            daily[date_key]['estimated'] = '**'

        # Gather styles if present
        if checkin['beer_type']:
            style = checkin['beer_type'].split(' -')[0].strip()
            if style not in styles:
                styles[style] = {'style': style, 'count': 0, 'rated': 0, 'total_score': 0}

            styles[style]['count'] += 1
            if checkin['rating_score']:
                styles[style]['rated'] += 1
                styles[style]['total_score'] += float(checkin['rating_score'])

        # Gather breweries if present
        if checkin.get('brewery_name', None):
            brewery_name = checkin['brewery_name']
            if brewery_name not in breweries:
                breweries[brewery_name] = {
                    'brewery': brewery_name,
                    'count': 0,
                    'rated': 0,
                    'total_score': 0,
                    'unique_rated': 0,
                    'unique_total_score': 0,
                    'unique_beers': [],
                    'rated_beers': {},  # collect repeat ratings for the same beer
                }
            breweries[brewery_name]['count'] += 1
            if checkin['rating_score']:
                breweries[brewery_name]['rated'] += 1
                breweries[brewery_name]['total_score'] += float(checkin['rating_score'])
                beer_name = checkin['beer_name']
                if beer_name not in breweries[brewery_name]['rated_beers']:
                    breweries[brewery_name]['rated_beers'][beer_name] = []
                breweries[brewery_name]['rated_beers'][beer_name].append(float(checkin['rating_score']))

    # Gather weeks
    weekly = {}
    for date_key in daily:

        # calculate week
        date = parse_date(date_key)
        iso_calendar = date.isocalendar()  # Y - W - dow
        week_key = '%d-W%02d' % iso_calendar[0:2]
        days_since_monday = iso_calendar[2] - 1
        monday = date - timedelta(days=days_since_monday)
        if week_key not in weekly:
            weekly[week_key] = {
                'week': week_key,
                'commencing': monday.date().isoformat(),
                'drinks': 0,
                'units': 0,
                'alcohol_ml': 0,
                'beverage_ml': 0,
                'estimated': '',
                'rated': 0,
                'total_score': 0.0,
            }

        for k in daily[date_key]:
            if k == 'estimated':
                if len(daily[date_key][k]) > len(weekly[week_key][k]):
                    weekly[week_key][k] = daily[date_key][k]

            else:
                weekly[week_key][k] += daily[date_key][k]

    if weekly_output:
        write_weekly_summary(weekly, weekly_output)

    if daily_output:
        write_daily_summary(daily, daily_output)

    if styles_output:
        write_styles_summary(styles, styles_output)

    if brewery_output:
        write_breweries_summary(breweries, brewery_output)


def write_weekly_summary(weekly, weekly_output):
    weekly_writer = csv.writer(weekly_output)
    keys = ['drinks', 'average_score', 'beverage_ml', 'alcohol_ml', 'units', 'estimated', ]
    output_row = ['week', 'commencing'] + keys
    weekly_writer.writerow(output_row)
    for week_key in weekly:
        week_row = weekly[week_key]
        # Process average scores
        week_row['average_score'] = round(week_row['total_score'] / week_row['rated'], 2) \
            if week_row['rated'] else None

        output_row = [week_key, week_row['commencing']]
        for k in keys:
            cell_value = week_row[k]
            if k not in ('estimated', 'average_score', 'total_score') and cell_value is not None:
                cell_value = round(cell_value, 1)
            output_row.append(cell_value)

        weekly_writer.writerow(output_row)


def write_daily_summary(daily, daily_output):
    keys = ['drinks', 'average_score', 'beverage_ml', 'alcohol_ml', 'units', 'estimated', ]
    daily_writer = csv.writer(daily_output)
    output_row = ['date'] + keys
    daily_writer.writerow(output_row)
    for date_key in daily:
        day_row = daily[date_key]
        # Process average scores
        day_row['average_score'] = round(day_row['total_score'] / day_row['rated'], 2) \
            if day_row['rated'] else None

        output_row = [date_key]
        for k in keys:
            cell_value = day_row[k]
            if k not in ('estimated', 'average_score', 'total_score') and cell_value is not None:
                cell_value = round(cell_value, 1)
            output_row.append(cell_value)

        daily_writer.writerow(output_row)


def write_styles_summary(styles, styles_output):
    style_list = []
    style_totals = {'count': 0, 'rated': 0, 'total_score': 0}
    for style in styles:
        style_summary = styles[style]
        style_summary['average_score'] = round(style_summary['total_score'] / style_summary['rated'], 2) \
            if style_summary['rated'] else None
        style_list.append(style_summary)

        style_totals['total_score'] += style_summary['total_score']
        style_totals['rated'] += style_summary['rated']
        style_totals['count'] += style_summary['count']
    style_list.sort(key=lambda b: (0 - b['count'], b['style']))
    styles_writer = csv.writer(styles_output)
    style_keys = ['style', 'count', 'rated', 'average_score']
    styles_writer.writerow(style_keys)
    for style in style_list:
        output_row = []
        for k in style_keys:
            output_row.append(style[k])
        styles_writer.writerow(output_row)
    styles_writer.writerow([])
    styles_writer.writerow(
        ['Total',
         style_totals['count'],
         style_totals['rated'],
         round(style_totals['total_score'] / style_totals['rated'], 2) if style_totals['rated'] else None
         ]
    )


def write_breweries_summary(breweries, brewery_output):
    for brewery_name in breweries:
        if breweries[brewery_name]['rated']:
            breweries[brewery_name]['average_score'] = \
                round(breweries[brewery_name]['total_score'] / breweries[brewery_name]['rated'], 2)
            for b in breweries[brewery_name]['rated_beers']:
                breweries[brewery_name]['unique_rated'] += 1
                breweries[brewery_name]['unique_total_score'] += \
                    sum(breweries[brewery_name]['rated_beers'][b]) / len(breweries[brewery_name]['rated_beers'][b])
                # Add the *average score for this beer's checkins* to the unique total score
            breweries[brewery_name]['unique_average_score'] = \
                round(breweries[brewery_name]['unique_total_score'] / breweries[brewery_name]['unique_rated'], 2)
        else:
            breweries[brewery_name]['average_score'] = ''
            breweries[brewery_name]['unique_average_score'] = ''

    brewery_list = list(breweries.values())
    brewery_list.sort(key=lambda b: ((0 - b['unique_average_score']) if b['unique_average_score'] else 0, b['brewery']))
    breweries_writer = csv.writer(brewery_output)
    brewery_keys = ['brewery', 'count', 'rated', 'average_score', 'unique_rated', 'unique_average_score']
    breweries_writer.writerow(brewery_keys)
    for brewery in brewery_list:
        output_row = []
        for k in brewery_keys:
            output_row.append(brewery[k])
        breweries_writer.writerow(output_row)


def run_cli():
    args = parse_cli_args()
    source = args.source
    dest = args.output
    source_data = json.loads(file_contents(source))
    if dest:
        output_handle = open(dest, 'w')
    else:
        output_handle = sys.stdout

    if args.weekly:
        analyze_checkins(source_data, weekly_output=output_handle)
    elif args.daily:
        analyze_checkins(source_data, daily_output=output_handle)
    elif args.style:
        analyze_checkins(source_data, styles_output=output_handle)
    elif args.brewery:
        analyze_checkins(source_data, brewery_output=output_handle)
    else:
        raise Exception('No report requested')

    if dest:
        output_handle.close()


if __name__ == '__main__':
    run_cli()
