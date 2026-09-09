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
    autocall_frequency,
    first_call_month,
    autocall_trigger,
    step_down_size,
    product_type,
    income_trigger,
    memory_coupon,
    coupon_pa,
    capital_barrier,
    notional
):
    df = df.copy()

    trade_date = pd.to_datetime(
        trade_date
    )

    if first_call_month > tenor_months:
        return None

    initial_rows = df[
        df[date_column] >= trade_date
    ]

    if initial_rows.empty:
        return None

    initial_row = initial_rows.iloc[0]

    actual_trade_date = initial_row[
        date_column
    ]

    initial_levels = initial_row[
        price_columns
    ]

    # =========================
    # Frequencies
    # =========================

    income_step_months = (
        frequency_to_months(
            income_frequency
        )
    )

    autocall_step_months = (
        frequency_to_months(
            autocall_frequency
        )
    )

    # =========================
    # Income observation schedule
    # =========================

    coupon_observation_months = list(
        range(
            income_step_months,
            tenor_months + 1,
            income_step_months
        )
    )

    # Final maturity always gets an
    # income observation
    if (
        tenor_months
        not in coupon_observation_months
    ):
        coupon_observation_months.append(
            tenor_months
        )

    coupon_observation_months = sorted(
        set(
            coupon_observation_months
        )
    )

    # =========================
    # Autocall observation schedule
    # =========================

    # Maturity is deliberately excluded
    # because the product cannot autocall
    # on the final maturity observation.
    autocall_observation_months = list(
        range(
            first_call_month,
            tenor_months,
            autocall_step_months
        )
    )

    autocall_observation_months = sorted(
        set(
            autocall_observation_months
        )
    )

    # =========================
    # Combined observation schedule
    # =========================

    all_observation_months = sorted(
        set(
            coupon_observation_months
            + autocall_observation_months
        )
    )

    maturity_date = (
        actual_trade_date
        + pd.DateOffset(
            months=tenor_months
        )
    )

    if maturity_date > df[date_column].max():
        return None

    # =========================
    # Coupon state
    # =========================

    missed_coupon_bank = 0
    total_coupon_paid_life = 0
    last_coupon_paid = 0
    coupons_paid_count = 0

    # Full regular-period coupon.
    #
    # If maturity is an irregular final
    # observation, it currently still pays
    # the full regular coupon by design.
    coupon_for_period = (
        coupon_pa
        * income_step_months
        / 12
    )

    # =========================
    # Observation loop
    # =========================

    for month in all_observation_months:

        is_coupon_observation = (
            month
            in coupon_observation_months
        )

        is_autocall_observation = (
            month
            in autocall_observation_months
        )

        scheduled_date = (
            actual_trade_date
            + pd.DateOffset(
                months=month
            )
        )

        available_rows = df[
            df[date_column] >= scheduled_date
        ]

        if available_rows.empty:
            return None

        obs_row = (
            available_rows.iloc[0]
        )

        obs_date = obs_row[
            date_column
        ]

        obs_levels = obs_row[
            price_columns
        ]

        performances = (
            obs_levels
            / initial_levels
        )

        worst_underlying = (
            performances.idxmin()
        )

        worst_performance = (
            performances.min()
        )

        worst_initial_level = (
            initial_levels[
                worst_underlying
            ]
        )

        worst_final_level = (
            obs_levels[
                worst_underlying
            ]
        )

        # Reset for this observation
        coupon_paid = 0
        last_coupon_paid = 0

        # =========================
        # Income observation
        # =========================

        if is_coupon_observation:

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

                    coupon_paid = (
                        coupon_for_period
                    )

                total_coupon_paid_life += (
                    coupon_paid
                )

                last_coupon_paid = (
                    coupon_paid
                )

                coupons_paid_count += round(
                    coupon_paid
                    / coupon_for_period
                )

            else:

                coupon_paid = 0
                last_coupon_paid = 0

                if memory_coupon == "Yes":

                    missed_coupon_bank += (
                        coupon_for_period
                    )

        # =========================
        # Autocall observation
        # =========================

        if is_autocall_observation:

            autocall_observation_number = (
                autocall_observation_months.index(
                    month
                )
            )

            if (
                product_type
                == "Step-Down Phoenix Autocall"
            ):

                current_autocall_trigger = (
                    autocall_trigger
                    - step_down_size
                    * autocall_observation_number
                )

            else:

                current_autocall_trigger = (
                    autocall_trigger
                )

            if (
                worst_performance
                >= current_autocall_trigger / 100
            ):

                payoff = (
                    notional
                    * (
                        1
                        + total_coupon_paid_life
                        / 100
                    )
                )

                observation_year = (
                    month / 12
                )

                annualised_return = (
                    (
                        (
                            1
                            + total_coupon_paid_life
                            / 100
                        )
                        ** (
                            1
                            / observation_year
                        )
                    )
                    - 1
                ) * 100

                flat_coupon_return_pa = (
                    (payoff - 100)
                    / observation_year
                )

                coupon_opportunities_until_exit = (
                    sum(
                        1
                        for coupon_month
                        in coupon_observation_months
                        if coupon_month <= month
                    )
                )

                if (
                    coupon_opportunities_until_exit
                    > 0
                ):

                    coupon_capture_rate = (
                        coupons_paid_count
                        / coupon_opportunities_until_exit
                        * 100
                    )

                else:

                    coupon_capture_rate = 0

                return {
                    "Trade Date": (
                        actual_trade_date.date()
                    ),

                    "Final Observation Date": (
                        obs_date.date()
                    ),

                    "Observation Month": month,

                    "Observation Year": round(
                        observation_year,
                        2
                    ),

                    "Autocall Trigger Used (%)": round(
                        current_autocall_trigger,
                        2
                    ),

                    "Income Trigger (%)": (
                        income_trigger
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
                            worst_performance
                            - 1
                        )
                        * 100,
                        2
                    ),

                    "Event": "Autocalled",

                    "Coupon Paid This Observation (%)": round(
                        coupon_paid,
                        2
                    ),

                    "Missed Coupon Bank (%)": round(
                        missed_coupon_bank,
                        2
                    ),

                    "Coupon Paid on Final Observation (%)": round(
                        coupon_paid,
                        2
                    ),

                    "Total Coupons Paid (%)": round(
                        total_coupon_paid_life,
                        2
                    ),

                    "Coupons Paid": (
                        coupons_paid_count
                    ),

                    "Coupon Opportunities Until Exit": (
                        coupon_opportunities_until_exit
                    ),

                    "Coupon Capture Rate (%)": round(
                        coupon_capture_rate,
                        2
                    ),

                    "Return (%)": round(
                        total_coupon_paid_life,
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

    # =========================
    # Maturity
    # =========================

    maturity_rows = df[
        df[date_column] >= maturity_date
    ]

    if maturity_rows.empty:
        return None

    maturity_row = (
        maturity_rows.iloc[0]
    )

    maturity_actual_date = (
        maturity_row[
            date_column
        ]
    )

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

    # =========================
    # Capital protection
    # =========================

    if (
        worst_final_performance
        >= capital_barrier / 100
    ):

        final_event = (
            "Matured, Capital Protected"
        )

        capital_payoff = (
            notional
        )

    else:

        final_event = (
            "Matured, Barrier Breached"
        )

        capital_payoff = (
            notional
            * worst_final_performance
        )

    # =========================
    # Final payoff
    # =========================

    payoff = (
        capital_payoff
        + notional
        * total_coupon_paid_life
        / 100
    )

    final_return = (
        payoff
        / notional
        - 1
    ) * 100

    annualised_return = (
        (
            (
                1
                + final_return
                / 100
            )
            ** (
                12
                / tenor_months
            )
        )
        - 1
    ) * 100

    observation_year = (
        tenor_months / 12
    )

    flat_coupon_return_pa = (
        (payoff - 100)
        / observation_year
    )

    coupon_opportunities_until_exit = (
        len(
            coupon_observation_months
        )
    )

    if (
        coupon_opportunities_until_exit
        > 0
    ):

        coupon_capture_rate = (
            coupons_paid_count
            / coupon_opportunities_until_exit
            * 100
        )

    else:

        coupon_capture_rate = 0

    return {
        "Trade Date": (
            actual_trade_date.date()
        ),

        "Final Observation Date": (
            maturity_actual_date.date()
        ),

        "Observation Month": (
            tenor_months
        ),

        "Observation Year": round(
            tenor_months / 12,
            2
        ),

        "Autocall Trigger Used (%)": (
            autocall_trigger
        ),

        "Income Trigger (%)": (
            income_trigger
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

        "Event": (
            final_event
        ),

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

        "Coupons Paid": (
            coupons_paid_count
        ),

        "Coupon Opportunities Until Exit": (
            coupon_opportunities_until_exit
        ),

        "Coupon Capture Rate (%)": round(
            coupon_capture_rate,
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
    autocall_frequency,
    first_call_month,
    autocall_trigger,
    income_trigger,
    memory_coupon,
    coupon_pa,
    capital_barrier,
    notional,
    step_down_size=0.0,
    product_type="Phoenix Autocall"
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
            autocall_frequency=autocall_frequency,
            first_call_month=first_call_month,
            autocall_trigger=autocall_trigger,
            step_down_size=step_down_size,
            product_type=product_type,
            income_trigger=income_trigger,
            memory_coupon=memory_coupon,
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
