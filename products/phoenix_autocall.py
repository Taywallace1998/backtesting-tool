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
    income_trigger,
    memory_coupon,
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

    coupon_observation_months = list(
        range(step_months, tenor_years * 12 + 1, step_months)
    )

    maturity_date = actual_trade_date + pd.DateOffset(years=tenor_years)

    if maturity_date > df[date_column].max():
        return None

    missed_coupon_bank = 0
    total_coupon_paid_life = 0
    last_coupon_paid = 0
    coupons_paid_count = 0

    for month in coupon_observation_months:
        can_autocall = month >= first_call_month
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

        coupon_for_period = coupon_pa * (step_months / 12)

        if product_type == "Step-Down Phoenix Autocall":
            observation_number = coupon_observation_months.index(month)

            current_autocall_trigger = (
                autocall_trigger
                - step_down_size * observation_number
            )
        else:
            current_autocall_trigger = autocall_trigger

        if can_autocall and worst_performance >= current_autocall_trigger / 100:

            if memory_coupon == "Yes":
                coupon_paid = coupon_for_period + missed_coupon_bank
                missed_coupon_bank = 0
            else:
                coupon_paid = coupon_for_period

            total_coupon_paid_life += coupon_paid
            last_coupon_paid = coupon_paid
            coupons_paid_count += round(
                coupon_paid / coupon_for_period
            )

            payoff = notional * (1 + total_coupon_paid_life / 100)

            annualised_return = (
                                        ((1 + total_coupon_paid_life / 100) ** (1 / (month / 12))) - 1
                                ) * 100

            coupon_opportunities_until_exit = (
                    coupon_observation_months.index(month) + 1
            )

            return {
                "Trade Date": actual_trade_date.date(),
                "Final Observation Date": obs_date.date(),
                "Observation Month": month,
                "Observation Year": round(month / 12, 2),
                "Autocall Trigger Used (%)": round(current_autocall_trigger, 2),
                "Income Trigger (%)": income_trigger,
                "Worst Underlying": worst_underlying,
                "Worst Initial Level": round(worst_initial_level, 2),
                "Worst Final Level": round(worst_final_level, 2),
                "Worst Performance (%)": round((worst_performance - 1) * 100, 2),
                "Event": "Autocalled",
                "Coupon Paid This Observation (%)": round(coupon_paid, 2),
                "Missed Coupon Bank (%)": round(missed_coupon_bank, 2),
                "Coupon Paid on Final Observation (%)": round(coupon_paid, 2),
                "Total Coupons Paid (%)": round(total_coupon_paid_life, 2),
                "Coupons Paid": coupons_paid_count,
                "Coupon Opportunities Until Exit": coupon_opportunities_until_exit,
                "Coupon Capture Rate (%)": round(
                coupons_paid_count / coupon_opportunities_until_exit * 100,
                2
                ),
                "Return (%)": round(total_coupon_paid_life, 2),
                "Annualised Return (%)": round(annualised_return, 2),
                "Payoff": round(payoff, 2)
            }

        elif worst_performance >= income_trigger / 100:

            if memory_coupon == "Yes":
                coupon_paid = coupon_for_period + missed_coupon_bank
                missed_coupon_bank = 0
            else:
                coupon_paid = coupon_for_period

            total_coupon_paid_life += coupon_paid
            last_coupon_paid = coupon_paid
            coupons_paid_count += round(
                coupon_paid / coupon_for_period
            )

        else:

            coupon_paid = 0

            if memory_coupon == "Yes":
                missed_coupon_bank += coupon_for_period

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
        capital_payoff = notional
    else:
        final_event = "Matured, Barrier Breached"
        capital_payoff = notional * worst_final_performance

    payoff = capital_payoff + (notional * total_coupon_paid_life / 100)

    final_return = (payoff / notional - 1) * 100

    annualised_return = (
                                ((1 + final_return / 100) ** (1 / tenor_years)) - 1
                        ) * 100

    coupon_opportunities_until_exit = len(coupon_observation_months)


    return {
        "Trade Date": actual_trade_date.date(),
        "Final Observation Date": maturity_actual_date.date(),
        "Observation Month": tenor_years * 12,
        "Observation Year": tenor_years,
        "Autocall Trigger Used (%)": autocall_trigger,
        "Income Trigger (%)": income_trigger,
        "Worst Underlying": worst_underlying,
        "Worst Initial Level": round(worst_initial_level, 2),
        "Worst Final Level": round(worst_final_level, 2),
        "Worst Performance (%)": round((worst_final_performance - 1) * 100, 2),
        "Event": final_event,
        "Coupon Paid This Observation (%)": round(last_coupon_paid, 2),
        "Missed Coupon Bank (%)": round(missed_coupon_bank, 2),
        "Coupon Paid on Final Observation (%)": round(last_coupon_paid, 2),
        "Total Coupons Paid (%)": round(total_coupon_paid_life, 2),
        "Coupons Paid": coupons_paid_count,
        "Coupon Opportunities Until Exit": coupon_opportunities_until_exit,
        "Coupon Capture Rate (%)": round(
            coupons_paid_count / coupon_opportunities_until_exit * 100,
            2
        ),
        "Return (%)": round(final_return, 2),
        "Annualised Return (%)": round(annualised_return, 2),
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
            "Reason": "There is not enough future data for the selected tenor."
        }])

    return pd.DataFrame(results)
