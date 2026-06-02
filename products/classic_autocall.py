import pandas as pd


def run_single_backtest(
    df,
    date_column,
    price_columns,
    trade_date,
    tenor_years,
    observation_frequency,
    first_call_month,
    autocall_trigger,
    step_down_size,
    product_type,
    coupon_pa,
    capital_barrier,
    notional
):
    df = df.copy()
    trade_date = pd.to_datetime(trade_date)

    initial_row = df[df[date_column] >= trade_date].iloc[0]
    actual_trade_date = initial_row[date_column]

    initial_levels = initial_row[price_columns]

    if observation_frequency == "Annual":
        step_months = 12
    elif observation_frequency == "Semi-Annual":
        step_months = 6
    elif observation_frequency == "Quarterly":
        step_months = 3
    else:
        step_months = 1

    observation_months = list(
        range(first_call_month, tenor_years * 12 + 1, step_months)
    )

    maturity_date = actual_trade_date + pd.DateOffset(years=tenor_years)

    if maturity_date > df[date_column].max():
        return None

    for month in observation_months:
        scheduled_date = actual_trade_date + pd.DateOffset(months=month)

        available_rows = df[df[date_column] >= scheduled_date]

        if available_rows.empty:
            return None

        obs_row = available_rows.iloc[0]
        obs_date = obs_row[date_column]

        obs_levels = obs_row[price_columns]
        performances = obs_levels / initial_levels

        worst_underlying = performances.idxmin()
        worst_performance = performances.min()
        worst_initial_level = initial_levels[worst_underlying]
        worst_final_level = obs_levels[worst_underlying]

        coupon_return = coupon_pa * (month / 12)

        if product_type == "Step-Down Autocall":
            observation_number = observation_months.index(month)

            current_autocall_trigger = (
                autocall_trigger
                - step_down_size * observation_number
            )

        else:
            current_autocall_trigger = autocall_trigger

        if worst_performance >= current_autocall_trigger / 100:
            payoff = notional * (1 + coupon_return / 100)

            return {
                "Trade Date": actual_trade_date.date(),
                "Final Observation Date": obs_date.date(),
                "Observation Month": month,
                "Observation Year": round(month / 12, 2),
                "Autocall Trigger Used (%)": round(current_autocall_trigger, 2),
                "Worst Underlying": worst_underlying,
                "Worst Initial Level": round(worst_initial_level, 2),
                "Worst Final Level": round(worst_final_level, 2),
                "Worst Performance (%)": round((worst_performance - 1) * 100, 2),
                "Event": "Autocalled",
                "Return (%)": round(coupon_return, 2),
                "Payoff": round(payoff, 2)
            }

    maturity_rows = df[df[date_column] >= maturity_date]

    if maturity_rows.empty:
        return None

    maturity_row = maturity_rows.iloc[0]
    maturity_actual_date = maturity_row[date_column]

    final_levels = maturity_row[price_columns]
    final_performances = final_levels / initial_levels

    worst_underlying = final_performances.idxmin()
    worst_final_performance = final_performances.min()
    worst_initial_level = initial_levels[worst_underlying]
    worst_final_level = final_levels[worst_underlying]

    if worst_final_performance >= capital_barrier / 100:
        final_event = "Matured, Capital Protected"
        final_return = 0
        payoff = notional
    else:
        final_event = "Matured, Barrier Breached"
        payoff = notional * worst_final_performance
        final_return = (payoff / notional - 1) * 100

    return {
        "Trade Date": actual_trade_date.date(),
        "Final Observation Date": maturity_actual_date.date(),
        "Observation Month": tenor_years * 12,
        "Observation Year": tenor_years,
        "Worst Underlying": worst_underlying,
        "Worst Initial Level": round(worst_initial_level, 2),
        "Worst Final Level": round(worst_final_level, 2),
        "Worst Performance (%)": round((worst_final_performance - 1) * 100, 2),
        "Event": final_event,
        "Return (%)": round(final_return, 2),
        "Payoff": round(payoff, 2)
    }


def run_backtest(
    df,
    date_column,
    price_columns,
    tenor_years,
    observation_frequency,
    first_call_month,
    autocall_trigger,
    step_down_size,
    product_type,
    coupon_pa,
    capital_barrier,
    notional
):
    df = df.copy()

    if not price_columns:
        return pd.DataFrame([{
            "Event": "No underlyings selected",
            "Reason": "Please select at least one underlying column."
        }])

    df[date_column] = pd.to_datetime(df[date_column])
    df = df.sort_values(date_column)
    df = df.dropna(subset=[date_column] + price_columns)

    results = []

    max_date = df[date_column].max()

    for rolling_trade_date in df[date_column]:
        maturity_date = rolling_trade_date + pd.DateOffset(years=tenor_years)

        if maturity_date > max_date:
            break

        result = run_single_backtest(
            df=df,
            date_column=date_column,
            price_columns=price_columns,
            trade_date=rolling_trade_date,
            tenor_years=tenor_years,
            observation_frequency=observation_frequency,
            first_call_month=first_call_month,
            autocall_trigger=autocall_trigger,
            step_down_size=step_down_size,
            product_type=product_type,
            coupon_pa=coupon_pa,
            capital_barrier=capital_barrier,
            notional=notional
        )

        if result is not None:
            results.append(result)

    if not results:
        return pd.DataFrame([{
            "Event": "No valid backtests",
            "Reason": "There is not enough future data for the selected tenor."
        }])

    return pd.DataFrame(results)