import unittest

from sheet_utils import ensure_worksheet_capacity


class FakeWorksheet:
    def __init__(self, rows, cols):
        self.row_count = rows
        self.col_count = cols
        self.resize_calls = []

    def resize(self, rows, cols):
        self.resize_calls.append((rows, cols))
        self.row_count = rows
        self.col_count = cols


class EnsureWorksheetCapacityTests(unittest.TestCase):
    def test_does_not_resize_when_range_fits(self):
        worksheet = FakeWorksheet(rows=12233, cols=30)

        ensure_worksheet_capacity(worksheet, required_rows=12233, required_cols=12)

        self.assertEqual([], worksheet.resize_calls)

    def test_expands_rows_before_writing_past_grid_limit(self):
        worksheet = FakeWorksheet(rows=12233, cols=30)

        ensure_worksheet_capacity(worksheet, required_rows=12234, required_cols=12)

        self.assertEqual([(13233, 30)], worksheet.resize_calls)

    def test_expands_columns_without_shrinking_rows(self):
        worksheet = FakeWorksheet(rows=100, cols=10)

        ensure_worksheet_capacity(worksheet, required_rows=50, required_cols=12)

        self.assertEqual([(100, 12)], worksheet.resize_calls)


if __name__ == '__main__':
    unittest.main()
