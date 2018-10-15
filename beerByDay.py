#!/usr/bin/env python

import re
import sys
import json
from typing import Optional
from dateutil.parser import parse as parse_date  # pipenv install  python-dateutil

DEFAULT_UNIT = 'pint'


def file_contents(file_path: str) -> Optional[str]:
    with open(file_path, 'r') as f:
        contents = f.readlines()
    return ''.join(contents)


def parse_measure(measure_string):
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


def measure_from_comment(comment: str) -> Optional[str]:
    measure_match = re.search(r'\[([^\[\]]+)\]', comment)  # evil thing to match!
    match_string = measure_match[1] if measure_match else None
    if match_string:
        drink_measure = parse_measure(match_string)
    else:
        drink_measure = None
    return drink_measure


def measure_from_serving(serving: str):
    serving = serving.lower()
    defaults = {
        'draft': 568 / 2,
        'cask': 568 / 2,
        'taster': 150,
        'bottle': 330,
        'can': 330
    }
    drink_measure = defaults[serving] if serving in defaults else None
    return drink_measure


source = sys.argv[1]

source_data = json.loads(file_contents(source))

daily = {}

for checkin in source_data:
    # fields of interest: comment, created_at, beer_abv, serving_type
    abv = float(checkin['beer_abv'])
    created_at = parse_date(checkin['created_at'])  # <class 'datetime.datetime'>
    date = created_at.date().isoformat()
    measure = measure_from_comment(checkin['comment'])
    if measure is None:
        measure = measure_from_serving(checkin['serving_type'])

    if measure and abv:
        alcohol_volume = float(measure) * abv / 100

        if date not in daily:
            daily[date] = 0

        daily[date] += alcohol_volume / 10

daily = {k: round(daily.get(k), 1) for k in daily}

for k in daily:
    print(','.join([k, str(daily[k])]))
