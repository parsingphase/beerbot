import unittest

from measures import MeasureProcessor, Region


class MeasureCalculationTests(unittest.TestCase):
    def test_eur_measure_processor(self):
        expectations = {
            'pint': 568,
            'oz': 28,
            'half': 284,
            '12ounces': 340,
            '33cl': 330,
            '440ml': 440
        }
        processor = MeasureProcessor(Region.EUROPE)
        for (source, expected) in expectations.items():
            self.assertEqual(processor.parse_measure(source), expected)

    def test_usa_measure_processor(self):
        expectations = {
            'pint': 473,
            'oz': 29,
            'half': 236,
            '12ounces': 355,
            '33cl': 330,
            '440ml': 440
        }
        processor = MeasureProcessor(Region.USA)
        for (source, expected) in expectations.items():
            self.assertEqual(processor.parse_measure(source), expected)


if __name__ == '__main__':
    unittest.main()
