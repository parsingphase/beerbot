#!/usr/bin/env python3

import argparse
import csv
import json
import sys
from datetime import timedelta
from typing import Dict, Optional, TextIO

from dateutil.parser import parse as parse_date  # pipenv install  python-dateutil

from measures import MeasureProcessor, Region
from utils import debug_print, file_contents, filter_source_data


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='Analyse consumption of alcoholic drinks from an Untappd JSON export file',
        usage=sys.argv[0] + ' SOURCE [--output OUTPUT] [--weekly|--daily|--style|--brewery] [--filter=…] [--help]',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=('Filter is based on JSON input keys.\nExample usages:\n'
                '    "--filter=venue_name=The Red Lion"\n    "--filter=created_at>2017-10-01"'
                )
    )
    parser.add_argument('source', help='Path to source file (export.json)')
    parser.add_argument('--output', required=False, help='Path to output file, STDOUT if not specified')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--daily', help='Summarise checkins by day', action='store_true')
    group.add_argument('--weekly', help='Summarise checkins by week', action='store_true')
    group.add_argument('--style', help='Summarise styles of drinks checked in', action='store_true')
    group.add_argument('--brewery', help='Summarise checkins by brewery', action='store_true')

    parser.add_argument('--filter',
                        metavar='RULE',
                        help='Filter input list by rule',
                        action='append')

    args = parser.parse_args()
    return args


def analyze_checkins(
        source_data: list,
        daily_output: TextIO = None,
        weekly_output: TextIO = None,
        styles_output: TextIO = None,
        brewery_output: TextIO = None,
) -> None:
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
    daily = {} if daily_output else None  # type: Optional[Dict]
    weekly = {} if weekly_output else None  # type: Optional[Dict]
    styles = {} if styles_output else None  # type: Optional[Dict]
    breweries = {} if brewery_output else None  # type: Optional[Dict]

    build_checkin_summaries(source_data, daily, weekly, styles, breweries)

    if weekly_output:
        write_weekly_summary(weekly, weekly_output)

    if daily_output:
        write_daily_summary(daily, daily_output)

    if styles_output:
        write_styles_summary(styles, styles_output)

    if brewery_output:
        write_breweries_summary(breweries, brewery_output)


def build_checkin_summaries(
        source_data: list,
        daily: dict = None,
        weekly: dict = None,
        styles: dict = None,
        breweries: dict = None
) -> None:
    """
    Build summaries to dictionaries as provided

    Args:
        source_data: Data unpacked from JSON source
        daily: dict to populate with daily data
        weekly: dict to populate with weekly data
        styles: dict to populate with style data
        breweries: dict to populate with brewery data

    Returns:

    """
    first_date = None
    last_date = None

    # Try and guess a default country for this user
    # First, by checkin
    # Else, by manufacturer (not really reliable, but only used if no located checkins)
    first_country = next(c['venue_country'] for c in source_data if c['venue_country'])
    if not first_country:
        first_country = next(c['brewery_country'] for c in source_data if c['brewery_country'])

    current_region = Region.USA if first_country == 'United States' else Region.EUROPE
    # FIXME check the first checkin location and use that as the default
    debug_print(f"Default region: {current_region}")

    # We need this to build with, even if we don't return it
    if daily is None:
        daily = {}

    for checkin in source_data:
        # fields of interest: comment, created_at, beer_abv, serving_type
        abv = float(checkin['beer_abv'])
        created_at = parse_date(checkin['created_at'])  # <class 'datetime.datetime'>
        created_at_date = created_at.date()
        date_key = created_at_date.isoformat()
        if first_date is None:
            first_date = created_at_date

        last_date = created_at_date

        if date_key not in daily:
            daily[date_key] = {
                'drinks': 0,
                'estimated': '',
                'rated': 0,
                'total_score': 0.0,
            }

        daily[date_key]['drinks'] += 1

        if checkin['rating_score']:
            daily[date_key]['rated'] += 1
            daily[date_key]['total_score'] += float(checkin['rating_score'])
            daily[date_key]['average'] = daily[date_key]['total_score'] / daily[date_key]['rated']

        # If bottle or can, set parser region by manufacturer
        if checkin['serving_type'] and checkin['serving_type'] in ['Can', 'Bottle'] and checkin['brewery_country']:
            if checkin['brewery_country'] == 'United States':
                checkin_region = Region.USA
            else:
                checkin_region = Region.EUROPE

            debug_print(f"Container manufacturer region: {current_region}")

        else:  # Otherwise, base it on location if available
            last_region = current_region
            if checkin['venue_country']:
                if checkin['venue_country'] == 'United States':
                    current_region = Region.USA
                else:
                    current_region = Region.EUROPE
                debug_print(f"Checkin region: {current_region}")

            if last_region != current_region:
                debug_print(f"** Switched region to {current_region}")

            checkin_region = current_region

        processor = MeasureProcessor(checkin_region)

        measure = processor.measure_from_comment(checkin['comment'])
        if measure is None:
            measure = processor.measure_from_serving(checkin['serving_type'])
            daily[date_key]['estimated'] = '*'

        if measure:
            if 'beverage_ml' not in daily[date_key]:
                daily[date_key]['beverage_ml'] = daily[date_key]['alcohol_ml'] = daily[date_key]['units'] = 0

            daily[date_key]['beverage_ml'] += measure
            if abv:
                alcohol_volume = float(measure) * abv / 100
                daily[date_key]['alcohol_ml'] += alcohol_volume
                daily[date_key]['units'] += alcohol_volume / 10

        else:
            daily[date_key]['estimated'] = '**'

        # Gather styles if present
        if styles is not None and checkin['beer_type']:
            style = checkin['beer_type'].split(' -')[0].strip()
            if style not in styles:
                styles[style] = {'style': style, 'count': 0, 'rated': 0, 'total_score': 0}

            styles[style]['count'] += 1
            if checkin['rating_score']:
                styles[style]['rated'] += 1
                styles[style]['total_score'] += float(checkin['rating_score'])

        # Gather breweries if present
        if breweries is not None and checkin.get('brewery_name', None):
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

    if not first_date or not last_date:  # Be explicit for the benefit of MyPy
        raise Exception('No dated checkins found')

    if weekly is not None:
        # Gather weeks
        for date_key in daily:

            # calculate week
            date = parse_date(date_key)
            iso_calendar = date.isocalendar()  # Y - W - dow
            week_key = '%d-W%02d' % iso_calendar[0:2]
            weekday = iso_calendar[2]
            days_since_monday = weekday - 1
            monday = date - timedelta(days=days_since_monday)

            if week_key in weekly:
                # Existing week
                weekly[week_key]['dry_days'] -= 1

            else:
                # New week
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
                    'dry_days': 6,
                }

            for k in daily[date_key]:
                if k == 'estimated':
                    # Get the most uncertain, ie longest, estimate flag (* or **) in this time period
                    if len(daily[date_key][k]) > len(weekly[week_key][k]):
                        weekly[week_key][k] = daily[date_key][k]

                elif k in daily[date_key] and k in weekly[week_key]:
                    weekly[week_key][k] += daily[date_key][k]

        # Fill in blank weeks
        iso_calendar = first_date.isocalendar()  # Y - W - dow
        weekday = iso_calendar[2]
        days_since_monday = weekday - 1
        next_monday = first_date - timedelta(days=days_since_monday)
        while next_monday <= last_date:
            iso_calendar = next_monday.isocalendar()  # Y - W - dow
            week_key = '%d-W%02d' % iso_calendar[0:2]
            if week_key not in weekly:
                weekly[week_key] = {
                    'week': week_key,
                    'commencing': next_monday.isoformat(),
                    'drinks': 0,
                    'units': 0,
                    'alcohol_ml': 0,
                    'beverage_ml': 0,
                    'estimated': '',
                    'rated': 0,
                    'total_score': 0.0,
                    'dry_days': 7,
                }
            next_monday += timedelta(weeks=1)


def write_weekly_summary(weekly, weekly_output):
    weekly_writer = csv.writer(weekly_output)
    keys = ['drinks', 'average_score', 'beverage_ml', 'alcohol_ml', 'units', 'dry_days', 'estimated']
    output_row = ['week', 'commencing'] + keys
    weekly_writer.writerow(output_row)

    for week_key in sorted(weekly):
        week_row = weekly[week_key]
        # Process average scores
        week_row['average_score'] = round(week_row['total_score'] / week_row['rated'], 2) \
            if week_row['rated'] else None

        output_row = [week_row['week'], week_row['commencing']]
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
    for date_key in sorted(daily):
        day_row = daily[date_key]
        # Process average scores
        day_row['average_score'] = round(day_row['total_score'] / day_row['rated'], 2) \
            if day_row['rated'] else None

        output_row = [date_key]
        for k in keys:
            cell_value = day_row[k] if k in day_row else None
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
    brewery_list.sort(
        key=lambda br: ((0 - br['unique_average_score']) if br['unique_average_score'] else 0, br['brewery'])
    )
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

    filter_strings = args.filter
    if filter_strings:
        source_data = filter_source_data(filter_strings, source_data)

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
