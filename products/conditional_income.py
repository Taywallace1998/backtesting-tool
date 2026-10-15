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
    income_trigger,
    memory_coupon,
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

    if income_frequency == "At Maturity":

        income_step_months = tenor_months

        coupon_observation_months = [
            tenor_months
        ]

    else:

        income_step_months = frequency_to_months(
            income_frequency
        )

        coupon_observation_months = list(
            range(
                income_step_months,
                tenor_months + 1,
                income_step_months
            )
        )

        # Match the Phoenix convention: maturity always gets
        # an income observation. If maturity is an irregular
        # final observation it receives the full regular coupon.
        if tenor_months not in coupon_observation_months:
            coupon_observation_months.append(
                tenor_months
            )

        coupon_observation_months = sorted(
            set(coupon_observation_months)
        )

    maturity_date = (
        actual_trade_date
        + pd.DateOffset(months=tenor_months)
    )

    if maturity_date > df[date_column].max():
        return None

    missed_coupon_bank = 0
    total_coupon_paid_life = 0
    last_coupon_paid = 0
    coupons_paid_count = 0

    if income_frequency == "At Maturity":

        coupon_for_period = (
            coupon_pa
            * tenor_months
            / 12
        )

    else:

        coupon_for_period = (
            coupon_pa
            * income_step_months
            / 12
        )

    final_obs_date = None
    final_obs_levels = None
    final_worst_underlying = None
    final_worst_performance = None
    final_worst_initial_level = None
    final_worst_level = None

    for month in coupon_observation_months:

        scheduled_date = (
            actual_trade_date
            + pd.DateOffset(months=month)
        )

        available_rows = df[
            df[date_column] >= scheduled_date
        ]

        if available_rows.empty:
            return None

        obs_row = available_rows.iloc[0]
        obs_date = obs_row[date_column]
        obs_levels = obs_row[price_columns]

        performances = (
            obs_levels
            / initial_levels
        )

        worst_underlying = performances.idxmin()
        worst_performance = performances.min()

        worst_initial_level = initial_levels[
            worst_underlying
        ]

        worst_level = obs_levels[
            worst_underlying
        ]

        coupon_paid = 0
        last_coupon_paid = 0

        if (
            worst_performance
            >= income_trigger / 100
        ):

            if memory_coupon == "Yes":
                coupon_paid = (
                    coupon_for_period
                    + missed_coupon_bank
                )
                missed_coupon_bank = 0
            else:
                coupon_paid = coupon_for_period

            total_coupon_paid_life += coupon_paid
            last_coupon_paid = coupon_paid

            coupons_paid_count += round(
                coupon_paid
                / coupon_for_period
            )

        else:

            if memory_coupon == "Yes":
                missed_coupon_bank += (
                    coupon_for_period
                )

        if month == tenor_months:
            final_obs_date = obs_date
            final_obs_levels = obs_levels
            final_worst_underlying = worst_underlying
            final_worst_performance = worst_performance
            final_worst_initial_level = (
                worst_initial_level
            )
            final_worst_level = worst_level

    if final_obs_levels is None:
        return None

    if (
        final_worst_performance
        >= capital_barrier / 100
    ):
        final_event = (
            "Matured, Capital Protected"
        )
        capital_payoff = notional
    else:
        final_event = (
            "Matured, Barrier Breached"
        )
        capital_payoff = (
            notional
            * final_worst_performance
        )

    payoff = (
        capital_payoff
        + notional
        * total_coupon_paid_life
        / 100
    )

    final_return = (
        payoff / notional - 1
    ) * 100

    observation_year = (
        tenor_months / 12
    )

    annualised_return = (
        (
            (1 + final_return / 100)
            ** (1 / observation_year)
        )
        - 1
    ) * 100

    flat_coupon_return_pa = (
        (payoff - 100)
        / observation_year
    )

    coupon_opportunities = len(
        coupon_observation_months
    )

    coupon_capture_rate = (
        coupons_paid_count
        / coupon_opportunities
        * 100
        if coupon_opportunities
        else 0
    )

    return {
        "Trade Date": actual_trade_date.date(),
        "Final Observation Date": (
            final_obs_date.date()
        ),
        "Observation Month": tenor_months,
        "Observation Year": round(
            observation_year,
            2
        ),
        "Income Frequency": income_frequency,
        "Income Trigger (%)": income_trigger,
        "Memory Coupon": memory_coupon,
        "Coupon p.a. (%)": coupon_pa,
        "Capital Barrier (%)": capital_barrier,
        "Worst Underlying": (
            final_worst_underlying
        ),
        "Worst Initial Level": round(
            final_worst_initial_level,
            2
        ),
        "Worst Final Level": round(
            final_worst_level,
            2
        ),
        "Worst Performance (%)": round(
            (
                final_worst_performance
                - 1
            )
            * 100,
            2
        ),
        "Event": final_event,
        "Coupon Paid This Observation (%)": round(
            last_coupon_paid,
            2
        ),
        "Missed Coupon Bank (%)": round(
            missed_coupon_bank,
            2
        ),
        "Coupon Paid on Final Observation (%)": round(
            last_coupon_paid,
            2
        ),
        "Total Coupons Paid (%)": round(
            total_coupon_paid_life,
            2
        ),
        "Coupons Paid": coupons_paid_count,
        "Coupon Opportunities Until Exit": (
            coupon_opportunities
        ),
        "Coupon Capture Rate (%)": round(
            coupon_capture_rate,
            2
        ),
        "Capital Redemption": round(
            capital_payoff,
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
    income_trigger,
    memory_coupon,
    coupon_pa,
    capital_barrier,
    notional
):
    df = df.copy()

    if not price_columns:
        return pd.DataFrame([{
            "Event": "No underlyings selected",
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
    max_date = df[date_column].max()

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
            income_trigger=income_trigger,
            memory_coupon=memory_coupon,
            coupon_pa=coupon_pa,
            capital_barrier=capital_barrier,
            notional=notional
        )

        if result is not None:
            results.append(result)

    if not results:
        return pd.DataFrame([{
            "Event": "No valid backtests",
            "Reason": (
                "There is not enough future data "
                "for the selected tenor."
            )
        }])

    return pd.DataFrame(results)
