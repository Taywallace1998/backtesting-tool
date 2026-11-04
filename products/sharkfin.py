import pandas as pd


def run_single_backtest(
    df,
    date_column,
    price_columns,
    trade_date,
    tenor_months,
    participation_rate,
    participation_strike,
    sharkfin_barrier,
    barrier_monitoring,
    rebate,
    protection_level
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

    final_performances = (
        final_levels
        / initial_levels
    )

    worst_underlying = (
        final_performances.idxmin()
    )

    worst_performance = (
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

    underlying_level = (
        worst_performance
        * 100
    )

    underlying_return = (
        underlying_level
        - 100
    )

    # =========================
    # Sharkfin barrier monitoring
    # =========================

    barrier_breached = False
    barrier_breach_underlying = None
    barrier_breach_date = None
    max_observed_level = None

    if barrier_monitoring == "European":

        maturity_relative_levels = (
            final_levels
            / initial_levels
            * 100
        )

        max_observed_level = (
            maturity_relative_levels.max()
        )

        qualifying = (
            maturity_relative_levels[
                maturity_relative_levels
                >= sharkfin_barrier
            ]
        )

        if not qualifying.empty:
            barrier_breached = True
            barrier_breach_underlying = (
                qualifying.idxmax()
            )
            barrier_breach_date = (
                maturity_actual_date
            )

    else:

        monitoring_data = df[
            (
                df[date_column]
                >= actual_trade_date
            )
            & (
                df[date_column]
                <= maturity_actual_date
            )
        ].copy()

        relative_levels = (
            monitoring_data[
                price_columns
            ]
            .div(
                initial_levels,
                axis="columns"
            )
            * 100
        )

        max_observed_level = (
            relative_levels.max().max()
        )

        breach_mask = (
            relative_levels
            >= sharkfin_barrier
        )

        if breach_mask.any().any():
            barrier_breached = True

            breach_rows = (
                breach_mask.any(
                    axis=1
                )
            )

            first_breach_position = (
                breach_rows.to_numpy()
                .nonzero()[0][0]
            )

            first_breach_index = (
                breach_rows.index[
                    first_breach_position
                ]
            )

            breached_columns = (
                breach_mask.loc[
                    first_breach_index
                ]
            )

            barrier_breach_underlying = (
                breached_columns[
                    breached_columns
                ].index[0]
            )

            barrier_breach_date = (
                monitoring_data.loc[
                    first_breach_index,
                    date_column
                ]
            )

    # =========================
    # Participation payoff
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

    if barrier_breached:

        payoff = (
            protection_level
            + rebate
        )

        event = (
            "Matured, Sharkfin Barrier Breached"
        )

        participation_return_used = 0.0

    else:

        participation_return_used = (
            participation_return
        )

        payoff = (
            protection_level
            + participation_return_used
        )

        if call_return > 0:
            event = (
                "Matured, Participation"
            )
        else:
            event = (
                "Matured, No Participation"
            )

    final_return = (
        payoff - 100
    )

    observation_year = (
        tenor_months / 12
    )

    annualised_return = (
        (
            (payoff / 100)
            ** (
                1 / observation_year
            )
        )
        - 1
    ) * 100

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
        "Barrier Monitoring": (
            barrier_monitoring
        ),
        "Sharkfin Barrier (%)": round(
            sharkfin_barrier,
            2
        ),
        "Barrier Breached": (
            "Yes"
            if barrier_breached
            else "No"
        ),
        "Barrier Breach Underlying": (
            barrier_breach_underlying
            if barrier_breach_underlying
            is not None
            else ""
        ),
        "Barrier Breach Date": (
            barrier_breach_date.date()
            if barrier_breach_date
            is not None
            else ""
        ),
        "Max Observed Level (%)": round(
            max_observed_level,
            2
        ),
        "Protection Level (%)": round(
            protection_level,
            2
        ),
        "Rebate (%)": round(
            rebate,
            2
        ),
        "Participation Rate (%)": round(
            participation_rate,
            2
        ),
        "Participation Strike (%)": round(
            participation_strike,
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
            participation_return_used,
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
    sharkfin_barrier,
    barrier_monitoring,
    rebate,
    protection_level
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

    max_date = (
        df[date_column].max()
    )

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
            sharkfin_barrier=sharkfin_barrier,
            barrier_monitoring=barrier_monitoring,
            rebate=rebate,
            protection_level=protection_level
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
                "There is not enough future "
                "data for the selected tenor."
            )
        }])

    return pd.DataFrame(
        results
    )
