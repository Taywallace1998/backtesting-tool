import streamlit as st
import pandas as pd

from products.classic_autocall import run_backtest as run_classic_backtest
from products.phoenix_autocall import run_backtest as run_phoenix_backtest
from products.participation import run_backtest as run_participation_backtest
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
# Autocall / Phoenix inputs
# =========================

if product_type != "Participation":

    observation_frequency = st.sidebar.selectbox(
        "Observation Frequency",
        ["Annual", "Semi-Annual", "Quarterly", "Monthly"],
        key="observation_frequency"
    )

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
        step=1.0,
        key="autocall_trigger"
    )

    if product_type in [
        "Step-Down Autocall",
        "Step-Down Phoenix Autocall"
    ]:
        step_down_size = st.sidebar.number_input(
            "Step-Down per Observation (%)",
            min_value=0.0,
            max_value=50.0,
            value=5.0,
            step=0.5,
            key="step_down_size"
        )
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
            step=1.0,
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
        key="coupon_pa"
    )

    capital_barrier = st.sidebar.number_input(
        "Capital Barrier (%)",
        min_value=0.0,
        max_value=100.0,
        value=60.0,
        step=1.0,
        key="capital_barrier"
    )

    # Participation variables not used
    participation_rate = None
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
        step=5.0,
        key="participation_rate"
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
            step=1.0,
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
            step=5.0,
            key="upside_cap"
        )
    else:
        upside_cap = None

    # Autocall variables not used
    observation_frequency = None
    first_call_month = None
    autocall_trigger = None
    step_down_size = 0.0
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

    if product_type == "Participation":

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
                "Value": f"{participation_rate}%"
            },
            {
                "Parameter": "Protection Type",
                "Value": protection_type
            },
            {
                "Parameter": "Protection Level",
                "Value": f"{protection_level}%"
            },
            {
                "Parameter": "Upside Cap",
                "Value": (
                    f"{upside_cap}"
                    if upside_cap is not None
                    else "None"
                )
            }
        ]

    else:

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
                "Parameter": "Observation Frequency",
                "Value": observation_frequency
            },
            {
                "Parameter": "First Call",
                "Value": f"{first_call_month} months"
            },
            {
                "Parameter": "Autocall Trigger",
                "Value": f"{autocall_trigger}%"
            },
            {
                "Parameter": "Coupon p.a.",
                "Value": f"{coupon_pa}%"
            },
            {
                "Parameter": "Capital Barrier",
                "Value": f"{capital_barrier}%"
            }
        ]

        if product_type in [
            "Step-Down Autocall",
            "Step-Down Phoenix Autocall"
        ]:
            summary_data.append({
                "Parameter": "Step-Down per Observation",
                "Value": f"{step_down_size}%"
            })

        if product_type in [
            "Phoenix Autocall",
            "Step-Down Phoenix Autocall"
        ]:
            summary_data.append({
                "Parameter": "Income Trigger",
                "Value": f"{income_trigger}%"
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

    if product_type in [
        "Step-Down Autocall",
        "Step-Down Phoenix Autocall"
    ]:

        if observation_frequency == "Annual":
            step_months = 12
        elif observation_frequency == "Semi-Annual":
            step_months = 6
        elif observation_frequency == "Quarterly":
            step_months = 3
        else:
            step_months = 1

        observation_months = list(
            range(
                first_call_month,
                tenor_months + 1,
                step_months
            )
        )

        if tenor_months not in observation_months:
            observation_months.append(
                tenor_months
            )

        stepdown_schedule = []

        for i, month in enumerate(
            observation_months
        ):

            trigger = (
                autocall_trigger
                - step_down_size * i
            )

            stepdown_schedule.append({
                "Observation": i + 1,
                "Month": month,
                "Autocall Trigger (%)": round(
                    trigger,
                    2
                )
            })

        stepdown_schedule_df = pd.DataFrame(
            stepdown_schedule
        )

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
                observation_frequency=observation_frequency,
                first_call_month=first_call_month,
                autocall_trigger=autocall_trigger,
                income_trigger=income_trigger,
                memory_coupon=memory_coupon,
                coupon_pa=coupon_pa,
                capital_barrier=capital_barrier,
                notional=notional,
                step_down_size=step_down_size,
                product_type=product_type
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

            summary_stats = pd.DataFrame({
                "Outcome": [
                    "Total Tested",
                    "Positive Return",
                    "Flat Return",
                    "Negative Return",
                    "Average Return",
                    "Average Annualised Return"
                ],
                "Number": [
                    total_tested,
                    positive_returns,
                    flat_returns,
                    negative_returns,
                    None,
                    None
                ],
                "Percentage": [
                    "100.00%",
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
                    f"{average_annualised_return:.2f}%"
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

            summary_stats = pd.DataFrame({
                "Outcome": [
                    "Total Tested",
                    "Total Autocalled",
                    "Returned Capital",
                    "Lost Capital",
                    "Check Total",
                    "Average Flat Coupon Return p.a.",
                    "Average Annualised Return"
                ],
                "Number": [
                    total_tested,
                    total_autocalled,
                    total_returned_capital,
                    total_lost_capital,
                    (
                        total_autocalled
                        + total_returned_capital
                        + total_lost_capital
                    ),
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
                    "100.00%",
                    f"{average_flat_coupon_return:.2f}%",
                    f"{average_annualised_return:.2f}%"
                ]
            })

        st.subheader("Backtest Summary")

        st.dataframe(
            summary_stats,
            use_container_width=True
        )

        # =========================
        # Autocall Distribution
        # =========================

        if product_type != "Participation":

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

        if len(price_columns) > 0:

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

        else:
            st.warning(
                "Please select at least one underlying."
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
            underlying_performance_data=rebased_df
        )

        st.download_button(
            label="📊 Download Excel Report",
            data=excel_file,
            file_name="backtest_results.xlsx",
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

        if product_type == "Participation":

            selected_inputs.update({
                "participation_rate": participation_rate,
                "protection_type": protection_type,
                "protection_level": protection_level,
                "upside_cap": upside_cap
            })

        else:

            selected_inputs.update({
                "observation_frequency": observation_frequency,
                "first_call_month": first_call_month,
                "autocall_trigger": autocall_trigger,
                "step_down_size": step_down_size,
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
