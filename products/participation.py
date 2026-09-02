import pandas as pd


def run_single_backtest(
    df,
    date_column,
    price_columns,
    trade_date,
    tenor_months,
    participation_rate,
    participation_strike,
    protection_type,
    protection_level,
    upside_cap
):
    df = df.copy()
    trade_date = pd.to_datetime(trade_date)

    initial_row = df[
        df[date_column] >= trade_date
    ].iloc[0]

    actual_trade_date = initial_row[
        date_column
    ]

    initial_levels = initial_row[
        price_columns
    ]

    maturity_date = (
        actual_trade_date
        + pd.DateOffset(
            months=tenor_months
        )
    )

    if maturity_date > df[date_column].max():
        return None

    maturity_rows = df[
        df[date_column] >= maturity_date
    ]

    if maturity_rows.empty:
        return None

    maturity_row = maturity_rows.iloc[0]

    maturity_actual_date = maturity_row[
        date_column
    ]

    final_levels = maturity_row[
        price_columns
    ]

    performances = (
        final_levels
        / initial_levels
    )

    worst_underlying = performances.idxmin()

    worst_performance = performances.min()

    worst_initial_level = initial_levels[
        worst_underlying
    ]

    worst_final_level = final_levels[
        worst_underlying
    ]

    # =========================
    # Underlying performance
    # =========================

    underlying_level = (
        worst_performance
        * 100
    )

    underlying_return = (
        underlying_level
        - 100
    )

    # =========================
    # Participation component
    # =========================

    call_return = max(
        underlying_level
        - participation_strike,
        0
    )

    participation_return = (
        call_return
        * participation_rate
        / 100
    )

    # =========================
    # Participation payoff
    # =========================

    if call_return > 0:

        if protection_type == "Partial Protected":

            payoff = (
                protection_level
                + participation_return
            )

        else:

            payoff = (
                100
                + participation_return
            )

        event = "Participated from Strike"

    # =========================
    # Downside protection
    # =========================

    else:

        if protection_type == "100% Protected":

            payoff = 100.0

            event = (
                "100% Capital Protected"
            )

        elif protection_type == "Partial Protected":

            payoff = protection_level

            event = (
                "Partial Protection Applied"
            )

        elif (
            protection_type
            == "Partial Protected with Put Spread"
        ):

            payoff = max(
                underlying_level,
                protection_level
            )

            if (
                underlying_level
                >= protection_level
            ):

                event = (
                    "Put Spread Downside"
                )

            else:

                event = (
                    "Put Spread Floor Applied"
                )

        else:

            payoff = 100.0

            event = "Matured"

    # =========================
    # Optional upside cap
    # =========================

    if upside_cap is not None:

        payoff = min(
            payoff,
            upside_cap
        )

    # =========================
    # Return calculations
    # =========================

    final_return = (
        payoff - 100
    )

    observation_year = (
        tenor_months / 12
    )

    annualised_return = (
        (
            (payoff / 100)
            ** (1 / observation_year)
        ) - 1
    ) * 100

    # =========================
    # Results
    # =========================

    return {
        "Trade Date": actual_trade_date.date(),
        "Maturity Date": maturity_actual_date.date(),

        "Observation Month": tenor_months,

        "Observation Year": round(
            observation_year,
            2
        ),

        "Protection Type": protection_type,

        "Protection Level (%)": (
            protection_level
        ),

        "Participation Rate (%)": (
            participation_rate
        ),

        "Participation Strike (%)": (
            participation_strike
        ),

        "Upside Cap": (
            upside_cap
            if upside_cap is not None
            else "None"
        ),

        "Worst Underlying": worst_underlying,

        "Worst Initial Level": round(
            worst_initial_level,
            2
        ),

        "Worst Final Level": round(
            worst_final_level,
            2
        ),

        "Underlying Level (%)": round(
            underlying_level,
            2
        ),

        "Underlying Performance (%)": round(
            underlying_return,
            2
        ),

        "Call Return (%)": round(
            call_return,
            2
        ),

        "Participation Return (%)": round(
            participation_return,
            2
        ),

        "Event": event,

        "Return (%)": round(
            final_return,
            2
        ),

        "Payoff": round(
            payoff,
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
    participation_rate,
    participation_strike,
    protection_type,
    protection_level,
    upside_cap
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
            participation_rate=participation_rate,
            participation_strike=participation_strike,
            protection_type=protection_type,
            protection_level=protection_level,
            upside_cap=upside_cap
        )

        if result is not None:

            results.append(
                result
            )

    if not results:

        return pd.DataFrame([{
            "Event": "No valid backtests",
            "Reason": (
                "There is not enough future data "
                "for the selected tenor."
            )
        }])

    return pd.DataFrame(
        results
    )
