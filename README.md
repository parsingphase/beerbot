## untappd-tools

Tools for processing [Untappd Supporter](https://untappd.com/supporter) export data

This is code documentation intended for technical users. General documentation can be found at 
[beerbot.phase.org](https://beerbot.phase.org) or in the [docs](docs/index.md) folder.

#### imbibed.py

Build a CSV of daily & weekly consumption from your Beer History JSON export.

To increase accuracy, include the measure size in square brackets in your checkin comments, eg `[third], [300ml], [2/3pint]`.
Otherwise standard sizes are guessed from the serving type; edit these default values to your needs.

Usage:

    ./imbibed.py data/input.json --output data/output.csv --weekly|--daily|--style|--brewery
   
Choose a summary type from one of `--weekly`, `--daily`, `--style`, `--brewery`   
    
Run with `--help` for further details

 **Note** This script is designed to help monitor healthy levels of consumption, not as a scorekeeper.
 
##### Filtering

You can use zero or more --filter clauses to select only certain rows, according to the JSON keys in the export.

The syntax is `"--filter=KEY|OPERATOR|VALUE"`, eg `"--filter=created_at>2018-11" "--filter=created_at<2019"`

Where:
 - `KEY` is the case sensitive JSON key from the source file. Useful ones include `created_at`, `venue_name`, `venue_country`
 - `OPERATOR` is one of: 
   - `=` Match
   - `^` No match
   - `>` Greater than
   - `<` Less than
   - `~` Starts with
 - `VALUE` is the value to compare against, in a case insensitive manner. Leaving the value blank with `=` allows matching of an empty field.
 Note that all values are processed as strings, so `created_at>2018-11` will include everything from 2018-11-01 onwards  
 
Use of quotes (`"`) around the arguments will usually be required to avoid them being intercepted by the shell command line.
 
#### stock_check.py
 
Generate a CSV taplist of beers, ordered by expiry date, from a JSON export of a detailed list, plus a summary of styles in
your collection.

To be effective, you'll need to populate best before dates, containers and quantities in your list.

Usage:

    ./stock_check.py data/input.json --output data/output.csv

Run with `--help` for further details

## Installation and requirements

These scripts are designed for use for those with some experience of running python code. 
End-user support cannot be provided.

Python 3 is required (see [https://realpython.com/installing-python/](https://realpython.com/installing-python/))

Everything below runs in your terminal.

Clone the repo with git (if you're familiar with that):
        
    git clone git@github.com:parsingphase/untappd-tools.git
    
Or grab a release from the [releases page](https://github.com/parsingphase/untappd-tools/releases) and unpack it.

Once you've got the code, change into its directory, then set it up. You've got two choices here:

### Install manually

 - Ensure you have python3 and pipenv installed, then run `pipenv install` (you only need to do this once).
 - Then load the environment with `pipenv shell`
 - You can now run the scripts as documented above:
   - `./stock_check.py --help` or `./imbibed.py --help`  
   
### Use the `init.sh` helper script

This will check your system, provide advice, fetch dependencies and load the environment:

 - run `./init.sh`  
 - You can now run the scripts as documented above:
   - `./stock_check.py --help` or `./imbibed.py --help`      
    
### Package & update Lambda:

    ./build.sh --upload
    
You can also validate the python code:    

    ./build.sh --validate
    
These arguments can be combined.    
    