## untappd-tools

Tools for processing [Untappd Supporter](https://untappd.com/supporter) export data

#### beerByDay.py

Build a CSV of daily & weekly consumption from your Beer History JSON export.

To increase accuracy, include the measure size in square brackets in your checkin comments, eg `[third], [300ml], [2/3pint]`.
Otherwise standard sizes are guessed from the serving type; edit these default values to your needs in `measure_from_serving()`.

Usage:

    ./beerByDay.py data/input.json --output data/output.csv [--weekly]
    
Run with `--help` for further details

 **Note** This script is designed to help monitor healthy levels of consumption, not as a scorekeeper.
 
#### stockCheck.py
 
Generate a CSV taplist of beers, ordered by expiry date, from a JSON export of a detailed list, plus a summary of styles in
your collection.

To be effective, you'll need to populate best before dates, containers and quantities in your list.

Usage:

    ./stockCheck.py data/input.json --output data/output.csv

Run with `--help` for further details

## Installation and requirements

These scripts are designed for use for those with some experience of running python code. 
End-user support cannot be provided.

Python 3 is required (see [https://realpython.com/installing-python/](https://realpython.com/installing-python/))

To install code & dependencies:
        
    git clone git@github.com:parsingphase/untappd-tools.git
    pipenv install
    
To run code, for example in a pipenv shell or a virtualenv:
    
    pipenv shell
    ./stockCheck.py data/input.json