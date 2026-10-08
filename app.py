import streamlit as st
import pandas as pd

from products.classic_autocall import run_backtest as run_classic_backtest
from products.phoenix_autocall import run_backtest as run_phoenix_backtest
from products.participation import run_backtest as run_participation_backtest
from products.fixed_income import run_backtest as run_fixed_income_backtest
from charts import (
    create_underlying_performance_chart,
    create_autocall_distribution_chart
)
from excel_export import create_excel_export


st.set_page_config(
    page_title="Autocall Backtesting Tool",
    layout="wide"
)

autocall_summary = None

if "results" not in st.session_state:
    st.session_state["results"] = None

if "summary_stats" not in st.session_state:
    st.session_state["summary_stats"] = None

if "autocall_summary" not in st.session_state:
    st.session_state["autocall_summary"] = None


st.title("Autocall Backtesting Tool")

st.write(
    "Upload historical price data, set the product parameters, "
    "and run the backtest."
)

# =========================
# Sidebar inputs
# =========================

st.sidebar.header("Product Parameters")

product_type = st.sidebar.selectbox(
    "Product Type",
    [
        "Classic Autocall",
        "Step-Down Autocall",
        "Phoenix Autocall",
        "Step-Down Phoenix Autocall",
        "Fixed Income",
        "Participation"
    ],
    key="product_type"
)

tenor_months = st.sidebar.number_input(
    "Tenor (months)",
    min_value=1,
    max_value=120,
    value=72,
    step=1,
    key="tenor_months"
)

# Fixed 100 reference amount for payoff calculations
notional = 100.0


# =========================
# Product inputs
# =========================

if product_type == "Fixed Income":

    income_frequency = st.sidebar.selectbox(
        "Income Frequency",
        ["Annual", "Semi-Annual", "Quarterly", "Monthly"],
        index=2,
        key="fixed_income_frequency"
    )

    coupon_pa = st.sidebar.number_input(
        "Fixed Coupon p.a. (%)",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=0.25,
        format="%.2f",
        key="fixed_income_coupon_pa"
    )

    capital_barrier = st.sidebar.number_input(
        "European Capital Barrier (%)",
        min_value=0.0,
        max_value=100.0,
        value=60.0,
        step=0.25,
        format="%.2f",
        key="fixed_income_capital_barrier"
    )

    observation_frequency = None
    autocall_frequency = None
    first_call_month = None
    autocall_trigger = None
    step_down_size = 0.0
    step_down_schedule = None
    income_trigger = None
    memory_coupon = "No"

    participation_rate = None
    participation_strike = None
    protection_type = None
    protection_level = None
    upside_cap = None

elif product_type != "Participation":

    if product_type in [
        "Phoenix Autocall",
        "Step-Down Phoenix Autocall"
    ]:

        income_frequency = st.sidebar.selectbox(
            "Income Frequency",
            ["Annual", "Semi-Annual", "Quarterly", "Monthly"],
            index=2,
            key="income_frequency"
        )

        autocall_frequency = st.sidebar.selectbox(
            "Autocall Frequency",
            ["Annual", "Semi-Annual", "Quarterly", "Monthly"],
            index=1,
            key="autocall_frequency"
        )

        # Retained for current Excel export compatibility.
        observation_frequency = autocall_frequency

    else:

        observation_frequency = st.sidebar.selectbox(
            "Observation Frequency",
            ["Annual", "Semi-Annual", "Quarterly", "Monthly"],
            key="observation_frequency"
        )

        income_frequency = None
        autocall_frequency = None

    first_call_month = st.sidebar.number_input(
        "First Call (months)",
        min_value=1,
        max_value=tenor_months,
        value=min(12, tenor_months),
        step=1,
        key="first_call_month"
    )

    autocall_trigger = st.sidebar.number_input(
        "Autocall Trigger (%)",
        min_value=0.0,
        max_value=200.0,
        value=100.0,
        step=0.25,
        format="%.2f",
        key="autocall_trigger"
    )

    step_down_schedule = None

    if product_type == "Step-Down Autocall":

        step_down_size = 0.0

        if observation_frequency == "Annual":
            schedule_step_months = 12
        elif observation_frequency == "Semi-Annual":
            schedule_step_months = 6
        elif observation_frequency == "Quarterly":
            schedule_step_months = 3
        else:
            schedule_step_months = 1

        stepdown_months = list(
            range(
                first_call_month,
                tenor_months + 1,
                schedule_step_months
            )
        )

        if tenor_months not in stepdown_months:
            stepdown_months.append(
                tenor_months
            )

        default_schedule_df = pd.DataFrame({
            "Observation": list(
                range(
                    1,
                    len(stepdown_months) + 1
                )
            ),
            "Month": stepdown_months,
            "Autocall Trigger (%)": [
                float(autocall_trigger)
                for _ in stepdown_months
            ]
        })

        st.sidebar.markdown(
            "#### Autocall Trigger Schedule"
        )

        edited_schedule_df = st.sidebar.data_editor(
            default_schedule_df,
            hide_index=True,
            disabled=[
                "Observation",
                "Month"
            ],
            column_config={
                "Autocall Trigger (%)": (
                    st.column_config.NumberColumn(
                        "Autocall Trigger (%)",
                        min_value=0.0,
                        max_value=200.0,
                        step=0.25,
                        format="%.2f"
                    )
                )
            },
            key="step_down_schedule_editor"
        )

        step_down_schedule = {
            int(row["Month"]): float(
                row["Autocall Trigger (%)"]
            )
            for _, row in (
                edited_schedule_df.iterrows()
            )
        }

    elif product_type == "Step-Down Phoenix Autocall":

        step_down_size = 0.0

        if autocall_frequency == "Annual":
            schedule_step_months = 12
        elif autocall_frequency == "Semi-Annual":
            schedule_step_months = 6
        elif autocall_frequency == "Quarterly":
            schedule_step_months = 3
        else:
            schedule_step_months = 1

        # Final maturity is excluded because
        # Phoenix cannot autocall at maturity.
        stepdown_months = list(
            range(
                first_call_month,
                tenor_months,
                schedule_step_months
            )
        )

        default_schedule_df = pd.DataFrame({
            "Observation": list(
                range(
                    1,
                    len(stepdown_months) + 1
                )
            ),
            "Month": stepdown_months,
            "Autocall Trigger (%)": [
                float(autocall_trigger)
                for _ in stepdown_months
            ]
        })

        st.sidebar.markdown(
            "#### Autocall Trigger Schedule"
        )

        edited_schedule_df = st.sidebar.data_editor(
            default_schedule_df,
            hide_index=True,
            disabled=[
                "Observation",
                "Month"
            ],
            column_config={
                "Autocall Trigger (%)": (
                    st.column_config.NumberColumn(
                        "Autocall Trigger (%)",
                        min_value=0.0,
                        max_value=200.0,
                        step=0.25,
                        format="%.2f"
                    )
                )
            },
            key="phoenix_step_down_schedule_editor"
        )

        step_down_schedule = {
            int(row["Month"]): float(
                row["Autocall Trigger (%)"]
            )
            for _, row in (
                edited_schedule_df.iterrows()
            )
        }

    else:
        step_down_size = 0.0

    if product_type in [
        "Phoenix Autocall",
        "Step-Down Phoenix Autocall"
    ]:

        income_trigger = st.sidebar.number_input(
            "Income Trigger (%)",
            min_value=0.0,
            max_value=200.0,
            value=70.0,
            step=0.25,
            format="%.2f",
            key="income_trigger"
        )

        memory_coupon = st.sidebar.selectbox(
            "Memory Coupon",
            ["Yes", "No"],
            key="memory_coupon"
        )

    else:
        income_trigger = None
        memory_coupon = "No"

    coupon_pa = st.sidebar.number_input(
        "Coupon p.a. (%)",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=0.25,
        format="%.2f",
        key="coupon_pa"
    )

    capital_barrier = st.sidebar.number_input(
        "Capital Barrier (%)",
        min_value=0.0,
        max_value=100.0,
        value=60.0,
        step=0.25,
        format="%.2f",
        key="capital_barrier"
    )

    # Participation variables not used
    participation_rate = None
    participation_strike = None
    protection_type = None
    protection_level = None
    upside_cap = None


# =========================
# Participation inputs
# =========================

else:

    participation_rate = st.sidebar.number_input(
        "Participation Rate (%)",
        min_value=0.0,
        max_value=1000.0,
        value=150.0,
        step=0.25,
        format="%.2f",
        key="participation_rate"
    )

    participation_strike = st.sidebar.number_input(
        "Participation Strike (%)",
        min_value=0.0,
        max_value=200.0,
        value=100.0,
        step=0.25,
        format="%.2f",
        key="participation_strike"
    )

    protection_type = st.sidebar.selectbox(
        "Protection Type",
        [
            "100% Protected",
            "Partial Protected",
            "Partial Protected with Put Spread"
        ],
        key="protection_type"
    )

    if protection_type == "100% Protected":
        protection_level = 100.0

    else:
        protection_level = st.sidebar.number_input(
            "Protection Level (%)",
            min_value=0.0,
            max_value=100.0,
            value=95.0,
            step=0.25,
            format="%.2f",
            key="protection_level"
        )

    apply_upside_cap = st.sidebar.checkbox(
        "Apply Upside Cap",
        value=False,
        key="apply_upside_cap"
    )

    if apply_upside_cap:
        upside_cap = st.sidebar.number_input(
            "Maximum Payoff",
            min_value=100.0,
            max_value=1000.0,
            value=150.0,
            step=0.25,
            format="%.2f",
            key="upside_cap"
        )
    else:
        upside_cap = None

    # Autocall variables not used
    observation_frequency = None
    income_frequency = None
    autocall_frequency = None
    first_call_month = None
    autocall_trigger = None
    step_down_size = 0.0
    step_down_schedule = None
    income_trigger = None
    memory_coupon = "No"
    coupon_pa = None
    capital_barrier = None


# =========================
# File upload
# =========================

st.header("1. Upload Data")

uploaded_file = st.file_uploader(
    "Upload historical price data",
    type=["xlsx", "csv"],
    key="historical_price_data_upload"
)

if uploaded_file is not None:

    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success("File uploaded successfully.")

    st.subheader("Data Preview")

    st.dataframe(
        df.head(20),
        use_container_width=True
    )

    st.subheader("Available Columns")

    st.write(list(df.columns))

    date_column = st.selectbox(
        "Select date column",
        df.columns,
        key="date_column"
    )

    price_columns = st.multiselect(
        "Select underlying columns (up to 5)",
        df.columns,
        max_selections=5,
        key="price_columns"
    )

    # =========================
    # Product Summary
    # =========================

    st.header("2. Product Summary")

    if product_type == "Fixed Income":

        summary_data = [
            {
                "Parameter": "Product Type",
                "Value": product_type
            },
            {
                "Parameter": "Tenor",
                "Value": f"{tenor_months} months"
            },
            {
                "Parameter": "Income Frequency",
                "Value": income_frequency
            },
            {
                "Parameter": "Fixed Coupon p.a.",
                "Value": f"{coupon_pa:.2f}%"
            },
            {
                "Parameter": "European Capital Barrier",
                "Value": f"{capital_barrier:.2f}%"
            }
        ]

    elif product_type == "Participation":

        summary_data = [
            {
                "Parameter": "Product Type",
                "Value": product_type
            },
            {
                "Parameter": "Tenor",
                "Value": f"{tenor_months} months"
            },
            {
                "Parameter": "Participation Rate",
                "Value": f"{participation_rate:.2f}%"
            },
            {
                "Parameter": "Participation Strike",
                "Value": f"{participation_strike:.2f}%"
            },
            {
                "Parameter": "Protection Type",
                "Value": protection_type
            }
        ]

        if protection_type != "100% Protected":
            summary_data.append({
                "Parameter": "Protection Level",
                "Value": f"{protection_level:.2f}%"
            })

        summary_data.append({
            "Parameter": "Upside Cap",
            "Value": (
                f"{upside_cap:.2f}%"
                if upside_cap is not None
                else "None"
            )
        })

    else:

        summary_data = [
            {
                "Parameter": "Product Type",
                "Value": product_type
            },
            {
                "Parameter": "Tenor",
                "Value": f"{tenor_months} months"
            }
        ]

        if product_type in [
            "Phoenix Autocall",
            "Step-Down Phoenix Autocall"
        ]:

            summary_data.extend([
                {
                    "Parameter": "Income Frequency",
                    "Value": income_frequency
                },
                {
                    "Parameter": "Autocall Frequency",
                    "Value": autocall_frequency
                }
            ])

        else:

            summary_data.append({
                "Parameter": "Observation Frequency",
                "Value": observation_frequency
            })

        summary_data.extend([
            {
                "Parameter": "First Call",
                "Value": f"{first_call_month} months"
            },
            {
                "Parameter": "Autocall Trigger",
                "Value": f"{autocall_trigger:.2f}%"
            },
            {
                "Parameter": "Coupon p.a.",
                "Value": f"{coupon_pa:.2f}%"
            },
            {
                "Parameter": "Capital Barrier",
                "Value": f"{capital_barrier:.2f}%"
            }
        ])

        if product_type == "Step-Down Autocall":

            schedule_text = ", ".join(
                f"{month}m: {trigger:.2f}%"
                for month, trigger in (
                    step_down_schedule.items()
                )
            )

            summary_data.append({
                "Parameter": "Autocall Trigger Schedule",
                "Value": schedule_text
            })

        elif product_type == "Step-Down Phoenix Autocall":

            schedule_text = ", ".join(
                f"{month}m: {trigger:.2f}%"
                for month, trigger in (
                    step_down_schedule.items()
                )
            )

            summary_data.append({
                "Parameter": "Autocall Trigger Schedule",
                "Value": schedule_text
            })

        if product_type in [
            "Phoenix Autocall",
            "Step-Down Phoenix Autocall"
        ]:
            summary_data.append({
                "Parameter": "Income Trigger",
                "Value": f"{income_trigger:.2f}%"
            })

            summary_data.append({
                "Parameter": "Memory Coupon",
                "Value": memory_coupon
            })

    summary = pd.DataFrame(summary_data)

    st.table(summary)

    # =========================
    # Step-down schedule preview
    # =========================

    if product_type == "Step-Down Autocall":

        stepdown_schedule_df = pd.DataFrame({
            "Observation": list(
                range(
                    1,
                    len(step_down_schedule) + 1
                )
            ),
            "Month": list(
                step_down_schedule.keys()
            ),
            "Autocall Trigger (%)": list(
                step_down_schedule.values()
            )
        })

        st.subheader("Step-Down Schedule")

        st.dataframe(
            stepdown_schedule_df,
            use_container_width=True
        )

    elif product_type == "Step-Down Phoenix Autocall":

        stepdown_schedule_df = pd.DataFrame({
            "Observation": list(
                range(
                    1,
                    len(step_down_schedule) + 1
                )
            ),
            "Month": list(
                step_down_schedule.keys()
            ),
            "Autocall Trigger (%)": list(
                step_down_schedule.values()
            )
        })

        st.subheader("Step-Down Schedule")

        st.dataframe(
            stepdown_schedule_df,
            use_container_width=True
        )

    # =========================
    # Run button
    # =========================

    st.header("3. Run Backtest")

    run_backtest_button = st.button(
        "Run Backtest",
        key="run_backtest_button"
    )

    if run_backtest_button:

        if not price_columns:
            st.warning(
                "Please select at least one underlying "
                "before running the backtest."
            )
            st.stop()

        autocall_fig = None
        underlying_fig = None
        autocall_summary = None

        # =========================
        # Classic / Step-Down
        # =========================

        if product_type in [
            "Classic Autocall",
            "Step-Down Autocall"
        ]:

            results = run_classic_backtest(
                df=df,
                date_column=date_column,
                price_columns=price_columns,
                tenor_months=tenor_months,
                observation_frequency=observation_frequency,
                first_call_month=first_call_month,
                autocall_trigger=autocall_trigger,
                step_down_size=step_down_size,
                product_type=product_type,
                coupon_pa=coupon_pa,
                step_down_schedule=step_down_schedule,
                capital_barrier=capital_barrier,
                notional=notional
            )

        # =========================
        # Phoenix
        # =========================

        elif product_type in [
            "Phoenix Autocall",
            "Step-Down Phoenix Autocall"
        ]:

            results = run_phoenix_backtest(
                df=df,
                date_column=date_column,
                price_columns=price_columns,
                tenor_months=tenor_months,
                income_frequency=income_frequency,
                autocall_frequency=autocall_frequency,
                first_call_month=first_call_month,
                autocall_trigger=autocall_trigger,
                income_trigger=income_trigger,
                memory_coupon=memory_coupon,
                coupon_pa=coupon_pa,
                capital_barrier=capital_barrier,
                notional=notional,
                step_down_size=step_down_size,
                product_type=product_type,
                step_down_schedule=step_down_schedule
            )

        # =========================
        # Fixed Income
        # =========================

        elif product_type == "Fixed Income":

            results = run_fixed_income_backtest(
                df=df,
                date_column=date_column,
                price_columns=price_columns,
                tenor_months=tenor_months,
                income_frequency=income_frequency,
                coupon_pa=coupon_pa,
                capital_barrier=capital_barrier,
                notional=notional
            )

        # =========================
        # Participation
        # =========================

        elif product_type == "Participation":

            results = run_participation_backtest(
                df=df,
                date_column=date_column,
                price_columns=price_columns,
                tenor_months=tenor_months,
                participation_rate=participation_rate,
                participation_strike=participation_strike,
                protection_type=protection_type,
                protection_level=protection_level,
                upside_cap=upside_cap
            )

        else:
            st.error(
                "This product type is not implemented yet."
            )
            st.stop()

        # =========================
        # Backtest Results
        # =========================

        st.subheader("Backtest Results")

        results_display = results.copy()

        if "Payoff" in results_display.columns:
            results_display["Payoff"] = (
                results_display["Payoff"].map(
                    lambda x: f"{x:,.2f}"
                )
            )

        st.dataframe(
            results_display,
            use_container_width=True
        )

        max_return = (
            results["Return (%)"].max()
        )

        min_return = (
            results["Return (%)"].min()
        )

        # =========================
        # Participation Summary
        # =========================

        if product_type == "Participation":

            total_tested = len(results)

            positive_returns = (
                results["Return (%)"] > 0
            ).sum()

            flat_returns = (
                results["Return (%)"] == 0
            ).sum()

            negative_returns = (
                results["Return (%)"] < 0
            ).sum()

            average_return = (
                results["Return (%)"].mean()
            )

            average_annualised_return = (
                results[
                    "Annualised Return (%)"
                ].mean()
            )

            above_participation_strike = (
                results["Underlying Level (%)"]
                > results["Participation Strike (%)"]
            ).sum()

            at_or_below_participation_strike = (
                results["Underlying Level (%)"]
                <= results["Participation Strike (%)"]
            ).sum()

            average_underlying_performance = (
                results[
                    "Underlying Performance (%)"
                ].mean()
            )

            average_participation_return = (
                results[
                    "Participation Return (%)"
                ].mean()
            )

            max_participation_return = (
                results[
                    "Participation Return (%)"
                ].max()
            )

            min_participation_return = (
                results[
                    "Participation Return (%)"
                ].min()
            )

            summary_rows = [
                {
                    "Outcome": "Total Tested",
                    "Number": total_tested,
                    "Percentage": "100.00%"
                },
                {
                    "Outcome": "Positive Return",
                    "Number": positive_returns,
                    "Percentage": (
                        f"{positive_returns / total_tested * 100:.2f}%"
                    )
                },
                {
                    "Outcome": "Flat Return",
                    "Number": flat_returns,
                    "Percentage": (
                        f"{flat_returns / total_tested * 100:.2f}%"
                    )
                },
                {
                    "Outcome": "Negative Return",
                    "Number": negative_returns,
                    "Percentage": (
                        f"{negative_returns / total_tested * 100:.2f}%"
                    )
                },
                {
                    "Outcome": "Average Return",
                    "Number": None,
                    "Percentage": f"{average_return:.2f}%"
                },
                {
                    "Outcome": "Average Annualised Return",
                    "Number": None,
                    "Percentage": (
                        f"{average_annualised_return:.2f}%"
                    )
                },
                {
                    "Outcome": "Max Return",
                    "Number": None,
                    "Percentage": f"{max_return:.2f}%"
                },
                {
                    "Outcome": "Min Return",
                    "Number": None,
                    "Percentage": f"{min_return:.2f}%"
                },
                {
                    "Outcome": (
                        "Underlying Above Participation Strike"
                    ),
                    "Number": above_participation_strike,
                    "Percentage": (
                        f"{above_participation_strike / total_tested * 100:.2f}%"
                    )
                },
                {
                    "Outcome": (
                        "Underlying At/Below Participation Strike"
                    ),
                    "Number": at_or_below_participation_strike,
                    "Percentage": (
                        f"{at_or_below_participation_strike / total_tested * 100:.2f}%"
                    )
                },
                {
                    "Outcome": "Average Underlying Performance",
                    "Number": None,
                    "Percentage": (
                        f"{average_underlying_performance:.2f}%"
                    )
                },
                {
                    "Outcome": "Average Participation Return",
                    "Number": None,
                    "Percentage": (
                        f"{average_participation_return:.2f}%"
                    )
                },
                {
                    "Outcome": "Max Participation Return",
                    "Number": None,
                    "Percentage": (
                        f"{max_participation_return:.2f}%"
                    )
                },
                {
                    "Outcome": "Min Participation Return",
                    "Number": None,
                    "Percentage": (
                        f"{min_participation_return:.2f}%"
                    )
                }
            ]

            if upside_cap is not None:

                cap_reached_count = (
                    results["Cap Reached"] == "Yes"
                ).sum()

                summary_rows.append({
                    "Outcome": "Cap Reached",
                    "Number": cap_reached_count,
                    "Percentage": (
                        f"{cap_reached_count / total_tested * 100:.2f}%"
                    )
                })

            if protection_type == "100% Protected":

                capital_protected_count = (
                    results["Event"]
                    == "100% Capital Protected"
                ).sum()

                summary_rows.append({
                    "Outcome": "100% Capital Protected",
                    "Number": capital_protected_count,
                    "Percentage": (
                        f"{capital_protected_count / total_tested * 100:.2f}%"
                    )
                })

            elif protection_type == "Partial Protected":

                partial_protection_count = (
                    results["Event"]
                    == "Partial Protection Applied"
                ).sum()

                summary_rows.append({
                    "Outcome": "Partial Protection Applied",
                    "Number": partial_protection_count,
                    "Percentage": (
                        f"{partial_protection_count / total_tested * 100:.2f}%"
                    )
                })

            elif (
                protection_type
                == "Partial Protected with Put Spread"
            ):

                put_spread_downside_count = (
                    results["Event"]
                    == "Put Spread Downside"
                ).sum()

                protection_floor_count = (
                    results["Event"]
                    == "Put Spread Floor Applied"
                ).sum()

                summary_rows.extend([
                    {
                        "Outcome": "Put Spread Downside",
                        "Number": put_spread_downside_count,
                        "Percentage": (
                            f"{put_spread_downside_count / total_tested * 100:.2f}%"
                        )
                    },
                    {
                        "Outcome": "Protection Floor Applied",
                        "Number": protection_floor_count,
                        "Percentage": (
                            f"{protection_floor_count / total_tested * 100:.2f}%"
                        )
                    }
                ])

            summary_stats = pd.DataFrame(
                summary_rows
            )

        # =========================
        # Fixed Income Summary
        # =========================

        elif product_type == "Fixed Income":

            total_tested = len(results)

            returned_full_capital = (
                results["Event"]
                == "Matured, Capital Protected"
            ).sum()

            barrier_breached = (
                results["Event"]
                == "Matured, Barrier Breached"
            ).sum()

            positive_returns = (
                results["Return (%)"] > 0
            ).sum()

            flat_returns = (
                results["Return (%)"] == 0
            ).sum()

            negative_returns = (
                results["Return (%)"] < 0
            ).sum()

            average_return = (
                results["Return (%)"].mean()
            )

            average_annualised_return = (
                results[
                    "Annualised Return (%)"
                ].mean()
            )

            summary_stats = pd.DataFrame({
                "Outcome": [
                    "Total Tested",
                    "Returned Full Capital",
                    "Barrier Breached",
                    "Positive Overall Return",
                    "Flat Overall Return",
                    "Negative Overall Return",
                    "Average Total Return",
                    "Average Annualised Return",
                    "Max Return",
                    "Min Return"
                ],
                "Number": [
                    total_tested,
                    returned_full_capital,
                    barrier_breached,
                    positive_returns,
                    flat_returns,
                    negative_returns,
                    None,
                    None,
                    None,
                    None
                ],
                "Percentage": [
                    "100.00%",
                    (
                        f"{returned_full_capital / total_tested * 100:.2f}%"
                    ),
                    (
                        f"{barrier_breached / total_tested * 100:.2f}%"
                    ),
                    (
                        f"{positive_returns / total_tested * 100:.2f}%"
                    ),
                    (
                        f"{flat_returns / total_tested * 100:.2f}%"
                    ),
                    (
                        f"{negative_returns / total_tested * 100:.2f}%"
                    ),
                    f"{average_return:.2f}%",
                    f"{average_annualised_return:.2f}%",
                    f"{max_return:.2f}%",
                    f"{min_return:.2f}%"
                ]
            })

        # =========================
        # Autocall Summary
        # =========================

        else:

            total_tested = len(results)

            total_autocalled = (
                results["Event"] == "Autocalled"
            ).sum()

            total_returned_capital = (
                results["Event"]
                == "Matured, Capital Protected"
            ).sum()

            total_lost_capital = (
                results["Event"]
                == "Matured, Barrier Breached"
            ).sum()

            average_flat_coupon_return = (
                results[
                    "Flat Coupon Return p.a. (%)"
                ].mean()
            )

            average_annualised_return = (
                results[
                    "Annualised Return (%)"
                ].mean()
            )

            # =========================
            # Phoenix income statistics
            # =========================

            if product_type in [
                "Phoenix Autocall",
                "Step-Down Phoenix Autocall"
            ]:

                total_income_payments_paid = int(
                    results[
                        "Coupons Paid"
                    ].sum()
                )

                total_income_opportunities = int(
                    results[
                        "Coupon Opportunities Until Exit"
                    ].sum()
                )

                total_income_payments_missed = (
                    total_income_opportunities
                    - total_income_payments_paid
                )

                returned_full_capital = (
                    total_autocalled
                    + total_returned_capital
                )

                returned_full_capital_percentage = (
                    returned_full_capital
                    / total_tested
                    * 100
                    if total_tested
                    else 0
                )

                coupon_paid_percentage = (
                    total_income_payments_paid
                    / total_income_opportunities
                    * 100
                    if total_income_opportunities
                    else 0
                )

                coupon_missed_percentage = (
                    total_income_payments_missed
                    / total_income_opportunities
                    * 100
                    if total_income_opportunities
                    else 0
                )

                summary_stats = pd.DataFrame({
                    "Outcome": [
                        "Total Tested",
                        "Total Autocalled",
                        "Returned Capital",
                        "Lost Capital",
                        "Returned Full Capital",
                        "Check Total",
                        "Total Income Payments Paid",
                        "Total Income Payments Missed",
                        "Average Flat Coupon Return p.a.",
                        "Average Annualised Return",
                        "Max Return",
                        "Min Return"
                    ],
                    "Number": [
                        total_tested,
                        total_autocalled,
                        total_returned_capital,
                        total_lost_capital,
                        returned_full_capital,
                        (
                            total_autocalled
                            + total_returned_capital
                            + total_lost_capital
                        ),
                        total_income_payments_paid,
                        total_income_payments_missed,
                        None,
                        None,
                        None,
                        None
                    ],
                    "Percentage": [
                        "100.00%",
                        (
                            f"{total_autocalled / total_tested * 100:.2f}%"
                        ),
                        (
                            f"{total_returned_capital / total_tested * 100:.2f}%"
                        ),
                        (
                            f"{total_lost_capital / total_tested * 100:.2f}%"
                        ),
                        f"{returned_full_capital_percentage:.2f}%",
                        "100.00%",
                        f"{coupon_paid_percentage:.2f}%",
                        f"{coupon_missed_percentage:.2f}%",
                        f"{average_flat_coupon_return:.2f}%",
                        f"{average_annualised_return:.2f}%",
                        f"{max_return:.2f}%",
                        f"{min_return:.2f}%"
                    ],
                    "Factsheet Headings": [
                        "Total Number Tested",
                        "% matured Early",
                        "% to reach Final Date",
                        "% barrier breach",
                        "% returned full capital",
                        "",
                        "% coupons paid",
                        "% coupons missed",
                        "Average Historic Return",
                        "",
                        "",
                        ""
                    ]
                })

            else:

                returned_full_capital = (
                    total_autocalled
                    + total_returned_capital
                )

                returned_full_capital_percentage = (
                    returned_full_capital
                    / total_tested
                    * 100
                    if total_tested
                    else 0
                )

                summary_stats = pd.DataFrame({
                    "Outcome": [
                        "Total Tested",
                        "Total Autocalled",
                        "Returned Capital",
                        "Lost Capital",
                        "Returned Full Capital",
                        "Check Total",
                        "Average Flat Coupon Return p.a.",
                        "Average Annualised Return",
                        "Max Return",
                        "Min Return"
                    ],
                    "Number": [
                        total_tested,
                        total_autocalled,
                        total_returned_capital,
                        total_lost_capital,
                        returned_full_capital,
                        (
                            total_autocalled
                            + total_returned_capital
                            + total_lost_capital
                        ),
                        None,
                        None,
                        None,
                        None
                    ],
                    "Percentage": [
                        "100.00%",
                        (
                            f"{total_autocalled / total_tested * 100:.2f}%"
                        ),
                        (
                            f"{total_returned_capital / total_tested * 100:.2f}%"
                        ),
                        (
                            f"{total_lost_capital / total_tested * 100:.2f}%"
                        ),
                        f"{returned_full_capital_percentage:.2f}%",
                        "100.00%",
                        f"{average_flat_coupon_return:.2f}%",
                        f"{average_annualised_return:.2f}%",
                        f"{max_return:.2f}%",
                        f"{min_return:.2f}%"
                    ],
                    "Factsheet Headings": [
                        "Total Number Tested",
                        "% matured Early",
                        "% to reach Final Date",
                        "% barrier breach",
                        "% returned full capital",
                        "",
                        "Average Historic Return",
                        "",
                        "",
                        ""
                    ]
                })

        # =========================
        # Display Backtest Summary
        # =========================

        st.subheader("Backtest Summary")

        st.dataframe(
            summary_stats,
            use_container_width=True
        )

        # =========================
        # Autocall Distribution
        # =========================

        if product_type not in [
            "Participation",
            "Fixed Income"
        ]:

            autocall_summary = (
                results[
                    results["Event"] == "Autocalled"
                ]
                .groupby("Observation Month")
                .size()
                .reset_index(
                    name="Autocalled"
                )
            )

            autocall_summary[
                "Autocall Test"
            ] = (
                autocall_summary[
                    "Observation Month"
                ]
                .astype(int)
                .astype(str)
                + " Months"
            )

            autocall_summary["%"] = (
                autocall_summary["Autocalled"]
                / total_tested
                * 100
            ).round(2)

            autocall_summary = (
                autocall_summary[
                    [
                        "Autocall Test",
                        "Autocalled",
                        "%"
                    ]
                ]
            )

            autocall_missed = (
                total_tested
                - total_autocalled
            )

            missed_row = pd.DataFrame([{
                "Autocall Test": "Autocall Missed",
                "Autocalled": autocall_missed,
                "%": round(
                    autocall_missed
                    / total_tested
                    * 100,
                    2
                )
            }])

            total_row = pd.DataFrame([{
                "Autocall Test": "Total",
                "Autocalled": total_tested,
                "%": 100.00
            }])

            autocall_summary = pd.concat(
                [
                    autocall_summary,
                    missed_row,
                    total_row
                ],
                ignore_index=True
            )

            autocall_summary["%"] = (
                autocall_summary["%"]
                .round(2)
                .astype(str)
                + "%"
            )

            st.subheader(
                "Autocall Distribution"
            )

            st.dataframe(
                autocall_summary,
                use_container_width=True
            )

            autocall_fig = (
                create_autocall_distribution_chart(
                    autocall_summary
                )
            )

            st.pyplot(
                autocall_fig
            )

        # =========================
        # Underlying Performance
        # =========================

        st.subheader(
            "Underlying Performance"
        )

        chart_df = df.copy()

        chart_df[date_column] = pd.to_datetime(
            chart_df[date_column],
            format="mixed",
            dayfirst=True,
            errors="coerce"
        )

        chart_df = chart_df.sort_values(
            date_column
        )

        chart_df = chart_df.dropna(
            subset=[
                date_column
            ] + price_columns
        )

        rebased_df = chart_df[
            [date_column] + price_columns
        ].copy()

        for col in price_columns:
            rebased_df[col] = (
                rebased_df[col]
                / rebased_df[col].iloc[0]
                * 100
            )

        underlying_fig = (
            create_underlying_performance_chart(
                rebased_df,
                date_column,
                price_columns
            )
        )

        st.pyplot(
            underlying_fig
        )

        # =========================
        # Excel Export
        # =========================

        excel_file = create_excel_export(
            product_type=product_type,
            tenor_months=tenor_months,
            observation_frequency=observation_frequency,
            first_call_month=first_call_month,
            autocall_trigger=autocall_trigger,
            step_down_size=step_down_size,
            income_trigger=income_trigger,
            memory_coupon=memory_coupon,
            coupon_pa=coupon_pa,
            capital_barrier=capital_barrier,
            notional=notional,
            date_column=date_column,
            price_columns=price_columns,
            results=results,
            summary_stats=summary_stats,
            autocall_summary=autocall_summary,
            underlying_performance_data=rebased_df,
            participation_rate=participation_rate,
            participation_strike=participation_strike,
            protection_type=protection_type,
            protection_level=protection_level,
            upside_cap=upside_cap,
            income_frequency=income_frequency,
            autocall_frequency=autocall_frequency,
            step_down_schedule=step_down_schedule
        )

        # =========================
        # Excel file name
        # =========================

        product_name = (
            product_type
            .replace(" ", "_")
            .replace("-", "_")
        )

        ticker_name = "_".join(
            str(col)
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            for col in price_columns
        )

        excel_file_name = (
            f"{product_name}_{ticker_name}_{tenor_months}M.xlsx"
            if ticker_name
            else f"{product_name}_{tenor_months}M.xlsx"
        )

        st.download_button(
            label="📊 Download Excel Report",
            data=excel_file,
            file_name=excel_file_name,
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

        # =========================
        # Selected Inputs
        # =========================

        st.write(
            "Selected inputs:"
        )

        selected_inputs = {
            "product_type": product_type,
            "tenor_months": tenor_months,
            "date_column": date_column,
            "price_columns": price_columns
        }

        if product_type == "Fixed Income":

            selected_inputs.update({
                "income_frequency": income_frequency,
                "coupon_pa": coupon_pa,
                "capital_barrier": capital_barrier
            })

        elif product_type == "Participation":

            selected_inputs.update({
                "participation_rate": participation_rate,
                "participation_strike": participation_strike,
                "protection_type": protection_type,
                "protection_level": protection_level,
                "upside_cap": upside_cap
            })

        else:

            if product_type in [
                "Phoenix Autocall",
                "Step-Down Phoenix Autocall"
            ]:

                selected_inputs.update({
                    "income_frequency": income_frequency,
                    "autocall_frequency": autocall_frequency,
                    "first_call_month": first_call_month,
                    "autocall_trigger": autocall_trigger,
                    "step_down_size": step_down_size,
                    "step_down_schedule": step_down_schedule,
                    "income_trigger": income_trigger,
                    "memory_coupon": memory_coupon,
                    "coupon_pa": coupon_pa,
                    "capital_barrier": capital_barrier
                })

            else:

                selected_inputs.update({
                    "observation_frequency": observation_frequency,
                    "first_call_month": first_call_month,
                    "autocall_trigger": autocall_trigger,
                    "step_down_size": step_down_size,
                    "step_down_schedule": step_down_schedule,
                    "income_trigger": income_trigger,
                    "memory_coupon": memory_coupon,
                    "coupon_pa": coupon_pa,
                    "capital_barrier": capital_barrier
                })

        st.json(
            selected_inputs
        )

        st.success(
            "Backtest completed successfully."
        )

else:

    st.info(
        "Please upload a CSV or Excel file to begin."
    )
