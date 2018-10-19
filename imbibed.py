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

DEFAULT_UNIT = 'pint'
DEFAULT_SERVING_SIZES = {'draft': 568 / 2, 'cask': 568 / 2, 'taster': 150, 'bottle': 330, 'can': 330}


def file_contents(file_path: str) -> Optional[str]:
    with open(file_path, 'r') as f:
        contents = f.readlines()
    return ''.join(contents)


def parse_measure(measure_string: str) -> int:
    divisors = {'quarter': 4, 'third': 3, 'half': 2}
    divisors_match = '|'.join(divisors.keys())
    units = {'ml': 1, 'litre': 1000, 'liter': 1000, 'pint': 568}
    unit_match = '|'.join(units.keys())
    candidate_matches = [
        '^(?P<unit>' + unit_match + ')$',
        '^(?P<quantity>\d+)(?P<unit>' + unit_match + ')$',
        '^(?P<divisor_text>' + divisors_match + ')(?P<unit>' + unit_match + ')?$',
        '^(?P<fraction>\d+/\d+)(?P<unit>' + unit_match + ')?$',
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
    return int(quantity)


def measure_from_comment(comment: str) -> Optional[int]:
    """
    Extract any mention of a measure (in square brackets) from the comment string on a checkin, if possible

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
        usage=sys.argv[0] + ' SOURCE [--output OUTPUT] [--weekly] [--help]'
    )
    parser.add_argument('source', help='Path to source file (export.json)')
    parser.add_argument('--output', required=False, help='Path to output file, STDOUT if not specified')
    parser.add_argument('--weekly', help='Count by week rather than day', action='store_true')
    args = parser.parse_args()
    return args


def analyze_checkins(
        source_data: list,
        daily_output: TextIO = None,
        weekly_output: TextIO = None,
        styles_output: TextIO = None
):
    """
    Build a summary of intake from the exported data, and save to buffer
    Args:
        source_data:
        daily_output:
        weekly_output:
        styles_output:

    Returns:

    """
    daily = {}
    keys = ['drinks', 'average_score', 'beverage_ml', 'alcohol_ml', 'units', 'estimated',]
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
                'drinks_rated': 0,
                'drinks_total_score': 0.0,
            }

        daily[date_key]['drinks'] += 1
        if checkin['rating_score']:
            daily[date_key]['drinks_rated'] += 1
            daily[date_key]['drinks_total_score'] += float(checkin['rating_score'])

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
                'drinks_rated': 0,
                'drinks_total_score': 0.0,
            }

        for k in daily[date_key]:
            if k == 'estimated':
                if len(daily[date_key][k]) > len(weekly[week_key][k]):
                    weekly[week_key][k] = daily[date_key][k]

            else:
                weekly[week_key][k] += daily[date_key][k]

    if weekly_output:
        weekly_writer = csv.writer(weekly_output)

        output_row = ['week', 'commencing'] + keys
        weekly_writer.writerow(output_row)

        for week_key in weekly:
            week_row = weekly[week_key]
            # Process average scores
            week_row['average_score'] = round(week_row['drinks_total_score'] / week_row['drinks_rated'], 2) \
                if week_row['drinks_rated'] else None

            output_row = [week_key, week_row['commencing']]
            for k in keys:
                cell_value = week_row[k]
                if k not in ('estimated', 'average_score', 'drinks_total_score') and cell_value is not None:
                    cell_value = round(cell_value, 1)
                output_row.append(cell_value)

            weekly_writer.writerow(output_row)

    if daily_output:
        daily_writer = csv.writer(daily_output)
        output_row = ['date'] + keys
        daily_writer.writerow(output_row)

        for date_key in daily:
            day_row = daily[date_key]
            # Process average scores
            day_row['average_score'] = round(day_row['drinks_total_score'] / day_row['drinks_rated'], 2) \
                if day_row['drinks_rated'] else None

            output_row = [date_key]
            for k in keys:
                cell_value = day_row[k]
                if k not in ('estimated', 'average_score', 'drinks_total_score') and cell_value is not None:
                    cell_value = round(cell_value, 1)
                output_row.append(cell_value)

            daily_writer.writerow(output_row)


def run_cli():
    args = parse_cli_args()
    source = args.source
    dest = args.output
    weekly = args.weekly
    source_data = json.loads(file_contents(source))
    if dest:
        output_handle = open(dest, 'w')
    else:
        output_handle = sys.stdout

    if weekly:
        analyze_checkins(source_data, weekly_output=output_handle)
    else:
        analyze_checkins(source_data, daily_output=output_handle)

    if dest:
        output_handle.close()


if __name__ == '__main__':
    run_cli()
