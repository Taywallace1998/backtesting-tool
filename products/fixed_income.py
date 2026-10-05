import pandas as pd


def frequency_to_months(frequency):
    if frequency == "Annual":
        return 12
    elif frequency == "Semi-Annual":
        return 6
    elif frequency == "Quarterly":
        return 3
    else:
        return 1


def run_single_backtest(
    df,
    date_column,
    price_columns,
    trade_date,
    tenor_months,
    income_frequency,
    coupon_pa,
    capital_barrier,
    notional
):
    df = df.copy()
    trade_date = pd.to_datetime(trade_date)

    initial_rows = df[
        df[date_column] >= trade_date
    ]

    if initial_rows.empty:
        return None

    initial_row = initial_rows.iloc[0]
    actual_trade_date = initial_row[date_column]
    initial_levels = initial_row[price_columns]

    maturity_date = (
        actual_trade_date
        + pd.DateOffset(months=tenor_months)
    )

    if maturity_date > df[date_column].max():
        return None

    maturity_rows = df[
        df[date_column] >= maturity_date
    ]

    if maturity_rows.empty:
        return None

    maturity_row = maturity_rows.iloc[0]
    maturity_actual_date = maturity_row[date_column]
    final_levels = maturity_row[price_columns]

    final_performances = (
        final_levels
        / initial_levels
    )

    worst_underlying = (
        final_performances.idxmin()
    )

    worst_final_performance = (
        final_performances.min()
    )

    worst_initial_level = (
        initial_levels[
            worst_underlying
        ]
    )

    worst_final_level = (
        final_levels[
            worst_underlying
        ]
    )

    income_step_months = (
        frequency_to_months(
            income_frequency
        )
    )

    full_income_periods = (
        tenor_months
        // income_step_months
    )

    stub_months = (
        tenor_months
        % income_step_months
    )

    regular_coupon = (
        coupon_pa
        * income_step_months
        / 12
    )

    total_income_paid = (
        full_income_periods
        * regular_coupon
    )

    income_payments = (
        full_income_periods
    )

    final_stub_coupon = 0.0

    if stub_months > 0:

        final_stub_coupon = (
            coupon_pa
            * stub_months
            / 12
        )

        total_income_paid += (
            final_stub_coupon
        )

        income_payments += 1

    if (
        worst_final_performance
        >= capital_barrier / 100
    ):

        event = (
            "Matured, Capital Protected"
        )

        capital_redemption = (
            notional
        )

    else:

        event = (
            "Matured, Barrier Breached"
        )

        capital_redemption = (
            notional
            * worst_final_performance
        )

    income_amount = (
        notional
        * total_income_paid
        / 100
    )

    payoff = (
        capital_redemption
        + income_amount
    )

    final_return = (
        payoff
        / notional
        - 1
    ) * 100

    observation_year = (
        tenor_months / 12
    )

    annualised_return = (
        (
            (
                1
                + final_return / 100
            )
            ** (
                1 / observation_year
            )
        )
        - 1
    ) * 100

    flat_coupon_return_pa = (
        final_return
        / observation_year
    )

    return {
        "Trade Date": (
            actual_trade_date.date()
        ),
        "Maturity Date": (
            maturity_actual_date.date()
        ),
        "Observation Month": (
            tenor_months
        ),
        "Observation Year": round(
            observation_year,
            2
        ),
        "Income Frequency": (
            income_frequency
        ),
        "Fixed Coupon p.a. (%)": round(
            coupon_pa,
            2
        ),
        "Income Payments": (
            income_payments
        ),
        "Regular Coupon (%)": round(
            regular_coupon,
            2
        ),
        "Final Stub Months": (
            stub_months
        ),
        "Final Stub Coupon (%)": round(
            final_stub_coupon,
            2
        ),
        "Total Income Paid (%)": round(
            total_income_paid,
            2
        ),
        "Capital Barrier (%)": round(
            capital_barrier,
            2
        ),
        "Worst Underlying": (
            worst_underlying
        ),
        "Worst Initial Level": round(
            worst_initial_level,
            2
        ),
        "Worst Final Level": round(
            worst_final_level,
            2
        ),
        "Worst Performance (%)": round(
            (
                worst_final_performance
                - 1
            )
            * 100,
            2
        ),
        "Event": event,
        "Capital Redemption": round(
            capital_redemption,
            2
        ),
        "Return (%)": round(
            final_return,
            2
        ),
        "Payoff": round(
            payoff,
            2
        ),
        "Flat Coupon Return p.a. (%)": round(
            flat_coupon_return_pa,
            2
        ),
        "Annualised Return (%)": round(
            annualised_return,
            2
        )
    }


def run_backtest(
    df,
    date_column,
    price_columns,
    tenor_months,
    income_frequency,
    coupon_pa,
    capital_barrier,
    notional
):
    df = df.copy()

    if not price_columns:

        return pd.DataFrame([{
            "Event": (
                "No underlyings selected"
            ),
            "Reason": (
                "Please select at least one "
                "underlying column."
            )
        }])

    df[date_column] = pd.to_datetime(
        df[date_column],
        format="mixed",
        dayfirst=True,
        errors="coerce"
    )

    df = df.sort_values(
        date_column
    )

    df = df.dropna(
        subset=[
            date_column
        ] + price_columns
    )

    results = []

    max_date = df[
        date_column
    ].max()

    for rolling_trade_date in df[
        date_column
    ]:

        maturity_date = (
            rolling_trade_date
            + pd.DateOffset(
                months=tenor_months
            )
        )

        if maturity_date > max_date:
            break

        result = run_single_backtest(
            df=df,
            date_column=date_column,
            price_columns=price_columns,
            trade_date=rolling_trade_date,
            tenor_months=tenor_months,
            income_frequency=income_frequency,
            coupon_pa=coupon_pa,
            capital_barrier=capital_barrier,
            notional=notional
        )

        if result is not None:
            results.append(
                result
            )

    if not results:

        return pd.DataFrame([{
            "Event": (
                "No valid backtests"
            ),
            "Reason": (
                "There is not enough future data "
                "for the selected tenor."
            )
        }])

    return pd.DataFrame(
        results
    )
