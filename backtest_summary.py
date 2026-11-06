import pandas as pd


def autocall_participation_summary(results):
    """Summarise hybrid outcomes; outcome percentages use all simulations."""
    total = len(results)
    called = results["Event"].eq("Autocalled")
    matured = results["Event"].eq("Matured, Participation")
    # Use index performance to distinguish growth from flat/down maturity.
    positive = matured & results["Worst Performance (%)"].gt(0)
    capital_only = matured & ~positive
    full_capital = results["Payoff"].ge(100)

    def count_row(label, mask, factsheet=""):
        count = int(mask.sum())
        return {
            "Outcome": label, "Number": count,
            "Percentage": f"{count / total * 100:.2f}%" if total else "N/A",
            "Factsheet Headings": factsheet
        }

    def value_row(label, value, suffix="%", factsheet=""):
        return {
            "Outcome": label, "Number": None,
            "Percentage": f"{value:.2f}{suffix}" if pd.notna(value) else "N/A",
            "Factsheet Headings": factsheet
        }

    return pd.DataFrame([
        {"Outcome": "Total Number Tested", "Number": total,
         "Percentage": "100.00%" if total else "N/A",
         "Factsheet Headings": "Total Number Tested"},
        count_row("% Autocalled", called, "% matured Early"),
        count_row("% Reaching Maturity", matured, "% to reach Final Date"),
        count_row("% Maturing with Positive Participation", positive),
        count_row("% Maturing at Capital Only", capital_only),
        count_row("% Returning Full Capital or More", full_capital, "% returned full capital"),
        value_row("Average Total Return", results["Return (%)"].mean()),
        value_row("Average Flat Coupon Return p.a.",
                  results["Flat Coupon Return p.a. (%)"].mean(),
                  factsheet="Average Historic Return"),
        value_row("Average Annualised Return", results["Annualised Return (%)"].mean()),
        value_row("Maximum Total Return", results["Return (%)"].max()),
        value_row("Minimum Total Return", results["Return (%)"].min()),
        value_row("Average Term (Years)", results["Observation Month"].mean() / 12, suffix=""),
        value_row("Average Return When Autocalled", results.loc[called, "Return (%)"].mean()),
        value_row("Average Return at Maturity", results.loc[matured, "Return (%)"].mean()),
    ])
