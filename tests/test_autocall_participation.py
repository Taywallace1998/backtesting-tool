import unittest
from io import BytesIO
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from products.classic_autocall import run_single_backtest, run_backtest
from excel_export import create_excel_export


class AutocallParticipationTests(unittest.TestCase):
    def prices(self, levels):
        return pd.DataFrame({"Date": pd.date_range("2020-01-01", periods=6, freq="YS"),
                             "Index": [100] + levels})

    def kwargs(self):
        return dict(date_column="Date", price_columns=["Index"],
                    tenor_months=60, observation_frequency="Annual",
                    first_call_month=12, autocall_trigger=100,
                    step_down_size=0, product_type="Autocall + Participation",
                    coupon_pa=8, capital_barrier=None, notional=100,
                    step_down_schedule={12:100, 24:101, 36:102, 48:103},
                    participation_rate=500)

    def single(self, levels, **overrides):
        args = self.kwargs()
        args.update(overrides)
        return run_single_backtest(df=self.prices(levels), trade_date="2020-01-01", **args)

    def test_each_trigger_and_accumulated_coupon(self):
        for year, trigger in enumerate([100, 101, 102, 103], 1):
            with self.subTest(year=year):
                levels = [90] * 5
                levels[year - 1] = trigger
                result = self.single(levels)
                self.assertEqual(result["Event"], "Autocalled")
                self.assertEqual(result["Observation Month"], year * 12)
                self.assertEqual(result["Payoff"], 100 + 8 * year)

    def test_maturity_participation_and_capital_floor(self):
        for final, payoff in [(110,150), (120,200), (100,100), (50,100), (0,100)]:
            with self.subTest(final=final):
                result = self.single([99,100,101,102,final])
                self.assertEqual(result["Event"], "Matured, Participation")
                self.assertEqual(result["Observation Month"], 60)
                self.assertEqual(result["Payoff"], payoff)

    def test_maturity_ignores_autocall_schedule_and_coupon(self):
        result = self.single([90,90,90,90,110],
                             step_down_schedule={12:100,24:101,36:102,48:103,60:100},
                             coupon_pa=99)
        self.assertEqual(result["Event"], "Matured, Participation")
        self.assertEqual(result["Payoff"], 150)

    def test_editable_participation_and_schedule(self):
        result = self.single([99,100,101,102,110], participation_rate=250)
        self.assertEqual(result["Payoff"], 125)
        result = self.single([90,95,90,90,110], step_down_schedule={12:100,24:95,36:90,48:85})
        self.assertEqual(result["Observation Month"], 24)
        self.assertEqual(result["Payoff"], 116)

    def test_existing_autocalls_keep_maturity_call(self):
        for product in ["Classic Autocall", "Step-Down Autocall"]:
            result = self.single([90,90,90,90,110], product_type=product, capital_barrier=60)
            self.assertEqual(result["Event"], "Autocalled")
            self.assertEqual(result["Payoff"], 140)

    def test_rolling_backtest_and_excel(self):
        args = self.kwargs()
        results = run_backtest(df=self.prices([99,100,101,102,110]), **args)
        self.assertEqual(len(results), 1)
        self.assertEqual(results.iloc[0]["Payoff"], 150)
        export_args = {k:v for k,v in args.items() if k != "step_down_size"}
        export_args.update(step_down_size=0, income_trigger=None, memory_coupon="No",
                           participation_strike=100, protection_level=100,
                           results=results, summary_stats=pd.DataFrame({"Total Tested":[1]}))
        book = load_workbook(create_excel_export(**export_args))
        inputs = dict(book["Inputs"].iter_rows(min_row=2, values_only=True))
        self.assertEqual(inputs["Product Type"], "Autocall + Participation")
        self.assertEqual(inputs["Capital Protection (%)"], 100)
        self.assertEqual(inputs["Participation Rate (%)"], 500)
        self.assertNotIn("Capital Barrier (%)", inputs)

    def test_modified_files_compile(self):
        for name in ["app.py", "excel_export.py", "products/classic_autocall.py"]:
            compile(Path(name).read_text(encoding="utf-8"), name, "exec")


if __name__ == "__main__":
    unittest.main()
