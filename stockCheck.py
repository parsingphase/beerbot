#!/usr/bin/env python

import csv
import sys
import json
from typing import Optional
from datetime import date
from dateutil.relativedelta import relativedelta


def file_contents(file_path: str) -> Optional[str]:
    with open(file_path, 'r') as f:
        contents = f.readlines()
    return ''.join(contents)


source = sys.argv[1]

source_data = json.loads(file_contents(source))

source_data.sort(key=lambda b: b['best_by_date_iso'])

thresholds = {
    'undated': {'description': 'Undated beers', 'ends': '0000-00-00'},
    'now': {'description': 'Expired beers', 'ends': date.today().strftime('%Y-%m-%d')},
    'month': {'description': 'Within one month',
              'ends': (date.today() + relativedelta(months=+1)).strftime('%Y-%m-%d')},
    'two': {'description': 'Within two months', 'ends': (date.today() + relativedelta(months=+2)).strftime('%Y-%m-%d')},
    'future': {'description': 'More than two months away'}
}

slices = {'undated': [], 'now': [], 'month': [], 'two': [], 'future': []}

for item in source_data:
    due = item['best_by_date_iso']
    if due <= thresholds['undated']['ends']:
        slices['undated'].append(item)
    elif due < thresholds['now']['ends']:
        slices['now'].append(item)
    elif due < thresholds['month']['ends']:
        slices['month'].append(item)
    elif due < thresholds['two']['ends']:
        slices['two'].append(item)
    else:
        slices['future'].append(item)

writer = csv.writer(sys.stdout)

for k in slices:
    print(thresholds[k]['description'] + ':', len(slices[k]), 'items')
    if len(slices[k]) == 0:
        print('(NONE)')
    else:
        for item in slices[k]:
            writer.writerow(
                [
                    item['best_by_date_iso'],
                    item['quantity'],
                    item['brewery_name'],
                    item['beer_name'],
                    item['beer_type']
                ]
            )
