import re
from typing import Optional


class Region:
    USA = 'usa'
    EUROPE = 'eur'


class Measure:
    """
    Measures in ml
    """
    OUNCE_UK = 28.4
    OUNCE_US = 29.6
    PINT_UK = 568
    PINT_US = 473  # 16 oz


class MeasureProcessor:
    DEFAULT_SERVING_SIZES = {
        Region.EUROPE: {
            'draft': Measure.PINT_UK / 2,  # Some personal preference here
            'cask': Measure.PINT_UK / 2,
            'taster': 150,
            'bottle': 330,
            'can': 330  # Starting to change towards 440
        },
        Region.USA: {  # Ref: https://beerconnoisseur.com/articles/popular-beer-sizes
            'draft': Measure.PINT_US,
            'cask': Measure.PINT_US,
            'taster': Measure.OUNCE_US * 4,
            'bottle': Measure.OUNCE_US * 12,
            'can': Measure.OUNCE_US * 12
        }
    }
    MAX_VALID_MEASURE = 2500  # For detection of valid inputs. More than a yard of ale or a Maß
    DEFAULT_UNIT = 'pint'

    def __init__(self, region):
        if region == Region.USA or region == Region.EUROPE:
            self.region = region
        else:
            raise Exception("Region in measure processor must be Region.USA or Region.EUROPE")

        self.units = {
            'ml': 1,
            'cl': 10,
            'litre': 1000,
            'liter': 1000,  # Accept variant spelling
            'sip': 25,
            'taste': 25,
        }

        if region == Region.USA:
            self.units['pint'] = Measure.PINT_US
            self.units['ounce'] = Measure.OUNCE_US
            self.units['oz'] = Measure.OUNCE_US
        else:
            self.units['pint'] = Measure.PINT_UK
            self.units['ounce'] = Measure.OUNCE_UK
            self.units['oz'] = Measure.OUNCE_UK

    def parse_measure(self, measure_string: str) -> int:
        """
        Read a measure as recorded in the comment field and parse it into a number of millilitres
        Args:
            measure_string: String as found in square brackets

        Returns:
            Integer number of ml
        """
        divisors = {'quarter': 4, 'third': 3, 'half': 2}
        divisor_match = '(?P<divisor_text>' + '|'.join(divisors.keys()) + ')'

        unit_match = '(?P<unit>' + '|'.join(self.units.keys()) + ')s?'  # allow plurals
        optional_unit_match = '(' + unit_match + ')?'
        fraction_match = r'(?P<fraction>\d+/\d+)'
        quantity_match = r'(?P<quantity>[\d\.]+)'
        optional_space = r'\s*'
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
            unit = match_dict['unit'] if 'unit' in match_dict and match_dict['unit'] is not None else self.DEFAULT_UNIT
            quantity = self.units[unit]
            if 'quantity' in match_dict:
                quantity *= float(match_dict['quantity'])
            elif 'divisor_text' in match_dict:
                quantity /= divisors[match_dict['divisor_text']]
            elif 'fraction' in match_dict:
                fraction_parts = [int(s) for s in match_dict['fraction'].split('/')]
                quantity = quantity * fraction_parts[0] / fraction_parts[1]

            if quantity > self.MAX_VALID_MEASURE:
                raise Exception('Measure of [%s] appears to be invalid. Did you miss out a unit?' % measure_string)

        return int(quantity) if quantity else None

    def measure_from_serving(self, serving: str) -> Optional[int]:
        """
        Get a default measure size from the serving style, if possible
        Args:
            serving: One of the Untappd serving names

        Returns:
            int measure in ml
        """
        serving = serving.lower()
        defaults = self.DEFAULT_SERVING_SIZES[self.region]
        drink_measure = defaults[serving] if serving in defaults else None
        return drink_measure

    def measure_from_comment(self, comment: str) -> Optional[int]:
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
            drink_measure = self.parse_measure(match_string)
        else:
            drink_measure = None
        return drink_measure
