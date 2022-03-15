from unittest import TestCase, main
from api.tools.round_numbers import interval_to_millisecs
from api.tools.enum_definitions import EnumDefinitions

class TestRoundNumbers(TestCase):

    def test_interval_to_millsecs(self):
        results = [900000, 60000, 180000, 300000, 1800000, 3600000, 7200000, 14400000, 21600000, 28800000, 43200000, 86400000, 259200000, 432000000, 2592000000]
        for interval in EnumDefinitions.chart_intervals:
            self.assertTrue(interval_to_millisecs(interval) in results)

if __name__ == "__main__":
    main()
