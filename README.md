## untappd-tools

Tools for processing [Untappd Supporter](https://untappd.com/supporter) export data

#### beerByDay.py

Export data from your Beer History JSON export to a CSV of daily consumption. 

To increase accuracy, include the measure size in square brackets in your checkin comments, eg `[third], [300ml], [2/3pint]`.
Otherwise standard sizes are guessed from the serving type; edit these default values to your needs in `measure_from_serving()`.

Usage:

    ./beerByDay.py data/Untappd-export.json > data/details.csv

To follow: selection of output file as an argument, summary options for week, month

 **Note** This script is designed to help monitor healthy levels of consumption, not as a scorekeeper.
 