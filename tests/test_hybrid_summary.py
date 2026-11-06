import unittest
from io import BytesIO
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from backtest_summary import autocall_participation_summary
from excel_export import create_excel_export


class HybridSummaryTests(unittest.TestCase):
    def setUp(self):
        self.results = pd.DataFrame({
            "Event": ["Autocalled", "Autocalled", "Matured, Participation",
                      "Matured, Participation", "Matured, Participation"],
            "Worst Performance (%)": [0, 1, 10, 0, -20],
            "Payoff": [108, 116, 150, 100, 100],
            "Return (%)": [8, 16, 50, 0, 0],
            "Flat Coupon Return p.a. (%)": [8, 8, 10, 0, 0],
            "Annualised Return (%)": [8, 7.7, 8.45, 0, 0],
            "Observation Month": [12, 24, 60, 60, 60]
        })

    def test_all_outcomes_and_denominators(self):
        summary = autocall_participation_summary(self.results).set_index("Outcome")
        self.assertEqual(len(summary), 14)
        self.assertEqual(summary.loc["% Autocalled", "Percentage"], "40.00%")
        self.assertEqual(summary.loc["% Reaching Maturity", "Percentage"], "60.00%")
        self.assertEqual(summary.loc["% Maturing with Positive Participation", "Percentage"], "20.00%")
        self.assertEqual(summary.loc["% Maturing at Capital Only", "Percentage"], "40.00%")
        self.assertEqual(summary.loc["% Returning Full Capital or More", "Percentage"], "100.00%")
        self.assertEqual(summary.loc["Average Total Return", "Percentage"], "14.80%")
        self.assertEqual(summary.loc["Average Flat Coupon Return p.a.", "Percentage"], "5.20%")
        self.assertEqual(summary.loc["Average Annualised Return", "Percentage"], "4.83%")
        self.assertEqual(summary.loc["Maximum Total Return", "Percentage"], "50.00%")
        self.assertEqual(summary.loc["Minimum Total Return", "Percentage"], "0.00%")
        self.assertEqual(summary.loc["Average Term (Years)", "Percentage"], "3.60")
        self.assertEqual(summary.loc["Average Return When Autocalled", "Percentage"], "12.00%")
        self.assertEqual(summary.loc["Average Return at Maturity", "Percentage"], "16.67%")
        self.assertNotIn("Average Simple Return p.a.", summary.index)

    def test_missing_outcome_groups_are_na(self):
        for event, missing_label in [
            ("Autocalled", "Average Return at Maturity"),
            ("Matured, Participation", "Average Return When Autocalled")
        ]:
            summary = autocall_participation_summary(
                self.results[self.results["Event"].eq(event)]
            ).set_index("Outcome")
            self.assertEqual(summary.loc[missing_label, "Percentage"], "N/A")

    def test_summary_is_exported_unchanged(self):
        summary = autocall_participation_summary(self.results)
        output = create_excel_export(
            product_type="Autocall + Participation", tenor_months=60,
            observation_frequency="Annual", first_call_month=12,
            autocall_trigger=100, step_down_size=0, income_trigger=None,
            memory_coupon="No", coupon_pa=8, capital_barrier=None,
            notional=100, date_column="Date", price_columns=["Index"],
            results=self.results, summary_stats=summary, participation_rate=500,
            step_down_schedule={12:100,24:101,36:102,48:103}
        )
        book = load_workbook(output)
        exported = list(book["Summary"].values)
        self.assertEqual(exported[0], tuple(summary.columns))
        self.assertEqual([row[0] for row in exported[1:]], list(summary["Outcome"]))
        self.assertEqual([row[2] for row in exported[1:]], list(summary["Percentage"]))

    def test_app_and_summary_compile(self):
        for name in ["app.py", "backtest_summary.py"]:
            compile(Path(name).read_text(encoding="utf-8"), name, "exec")


if __name__ == "__main__":
    unittest.main()
