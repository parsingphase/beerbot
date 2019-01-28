#!/usr/bin/env python

import argparse
import json
import re

import matplotlib.pyplot as plt

from utils import file_contents
from wordcloud import WordCloud, STOPWORDS


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='Create a word cloud from your checkin descriptions',
    )
    parser.add_argument('source', help='Path to source file (export.json)')
    parser.add_argument('--output', required=False, help='Path to output file, STDOUT if not specified')
    args = parser.parse_args()
    return args


def run_cli():
    args = parse_cli_args()
    source = args.source
    dest = args.output
    source_data = json.loads(file_contents(source))
    comments = [
        re.sub('\[.*\]', '', checkin['comment']).lower() for checkin in source_data
        if checkin['comment'] is not None and checkin['comment'] != ''
    ]

    # post-filter anything we've removed all text from
    comments = [comment for comment in comments if comment != '']

    #    print(comments)

    cloud = WordCloud(width=800, height=800,
                      background_color='white',
                      stopwords=STOPWORDS,
                      min_font_size=10).generate(' '.join(comments))

    # plot the WordCloud image
    plt.figure(figsize=(8, 8), facecolor=None)
    plt.imshow(cloud)
    plt.axis("off")
    plt.tight_layout(pad=0)

    if dest:
        plt.savefig(dest, format=dest.split('.')[-1])
    else:
        plt.show()


if __name__ == '__main__':
    run_cli()
