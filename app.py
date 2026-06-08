import streamlit as st
import pandas as pd

from products.classic_autocall import run_backtest as run_classic_backtest
from products.phoenix_autocall import run_backtest as run_phoenix_backtest
from charts import create_underlying_performance_chart, create_autocall_distribution_chart


st.set_page_config(
    page_title="Autocall Backtesting Tool",
    layout="wide"
)

st.title("Autocall Backtesting Tool")

st.write(
    "Upload historical price data, set the autocall parameters, "
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
        "Participation"
    ],
    key="product_type"
)

tenor_years = st.sidebar.number_input(
    "Tenor (years)",
    min_value=1,
    max_value=10,
    value=6,
    step=1,
    key="tenor_years"
)

observation_frequency = st.sidebar.selectbox(
    "Observation Frequency",
    ["Annual", "Semi-Annual", "Quarterly", "Monthly"],
    key="observation_frequency"
)

first_call_month = st.sidebar.number_input(
    "First Call (months)",
    min_value=1,
    max_value=60,
    value=12,
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

if product_type == "Step-Down Autocall":
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

if product_type == "Phoenix Autocall":
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

notional = st.sidebar.number_input(
    "Notional",
    min_value=1.0,
    value=1000.0,
    step=100.0,
    key="notional"
)

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
    # Parameter summary
    # =========================

    st.header("2. Product Summary")

    summary_data = [
        {"Parameter": "Product Type", "Value": product_type},
        {"Parameter": "Tenor", "Value": f"{tenor_years} years"},
        {"Parameter": "Observation Frequency", "Value": observation_frequency},
        {"Parameter": "First Call", "Value": f"{first_call_month} months"},
        {"Parameter": "Autocall Trigger", "Value": f"{autocall_trigger}%"},
        {"Parameter": "Coupon p.a.", "Value": f"{coupon_pa}%"},
        {"Parameter": "Capital Barrier", "Value": f"{capital_barrier}%"},
        {"Parameter": "Notional", "Value": notional}
    ]

    if product_type == "Step-Down Autocall":
        summary_data.append({
            "Parameter": "Step-Down per Observation",
            "Value": f"{step_down_size}%"
        })

    if product_type == "Phoenix Autocall":
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

    if product_type == "Step-Down Autocall":

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

        stepdown_schedule = []

        for i, month in enumerate(observation_months):
            trigger = autocall_trigger - step_down_size * i

            stepdown_schedule.append({
                "Observation": i + 1,
                "Month": month,
                "Autocall Trigger (%)": round(trigger, 2)
            })

        stepdown_schedule_df = pd.DataFrame(stepdown_schedule)

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

        if product_type in ["Classic Autocall", "Step-Down Autocall"]:

            results = run_classic_backtest(
                df=df,
                date_column=date_column,
                price_columns=price_columns,
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

        elif product_type == "Phoenix Autocall":

            results = run_phoenix_backtest(
                df=df,
                date_column=date_column,
                price_columns=price_columns,
                tenor_years=tenor_years,
                observation_frequency=observation_frequency,
                first_call_month=first_call_month,
                autocall_trigger=autocall_trigger,
                income_trigger=income_trigger,
                memory_coupon=memory_coupon,
                coupon_pa=coupon_pa,
                capital_barrier=capital_barrier,
                notional=notional
            )

        else:
            st.error("This product type is not implemented yet.")
            st.stop()

        st.subheader("Backtest Results")

        st.dataframe(
            results,
            use_container_width=True
        )

        # =========================
        # Summary statistics
        # =========================

        total_tested = len(results)

        total_autocalled = (
                results["Event"] == "Autocalled"
        ).sum()

        total_returned_capital = (
                results["Event"] == "Matured, Capital Protected"
        ).sum()

        total_lost_capital = (
                results["Event"] == "Matured, Barrier Breached"
        ).sum()

        summary_stats = pd.DataFrame({
            "Outcome": [
                "Total Tested",
                "Total Autocalled",
                "Returned Capital",
                "Lost Capital",
                "Check Total"
            ],
            "Number": [
                total_tested,
                total_autocalled,
                total_returned_capital,
                total_lost_capital,
                total_autocalled
                + total_returned_capital
                + total_lost_capital
            ],
            "Percentage": [
                "100.00%",
                f"{total_autocalled / total_tested * 100:.2f}%",
                f"{total_returned_capital / total_tested * 100:.2f}%",
                f"{total_lost_capital / total_tested * 100:.2f}%",
                "100.00%"
            ]
        })

        st.subheader("Backtest Summary")

        st.dataframe(
            summary_stats,
            use_container_width=True
        )

        # =========================
        # Autocall distribution
        # =========================

        if total_autocalled > 0:
            autocall_summary = (
                results[results["Event"] == "Autocalled"]
                .groupby("Observation Month")
                .size()
                .reset_index(name="Autocalled")
            )

            autocall_summary["Autocall Test"] = (
                    autocall_summary["Observation Month"]
                    .astype(int)
                    .astype(str)
                    + " Months"
            )

            autocall_summary["%"] = (
                    autocall_summary["Autocalled"]
                    / total_autocalled
                    * 100
            ).round(2)

            autocall_summary = autocall_summary[
                ["Autocall Test", "Autocalled", "%"]
            ]

            total_row = pd.DataFrame([{
                "Autocall Test": "Total",
                "Autocalled": autocall_summary["Autocalled"].sum(),
                "%": autocall_summary["%"].sum()
            }])

            autocall_summary = pd.concat(
                [autocall_summary, total_row],
                ignore_index=True
            )

            autocall_summary["%"] = (
                    autocall_summary["%"]
                    .round(2)
                    .astype(str)
                    + "%"
            )

            st.subheader("Autocall Distribution")

            st.dataframe(
                autocall_summary,
                use_container_width=True
            )

            autocall_fig = create_autocall_distribution_chart(
                autocall_summary
            )

            st.pyplot(autocall_fig)

        # =========================
        # Underlying performance chart
        # =========================

        st.subheader("Underlying Performance")

        chart_df = df.copy()

        chart_df[date_column] = pd.to_datetime(
            chart_df[date_column]
        )

        chart_df = chart_df.sort_values(date_column)

        chart_df = chart_df.dropna(
            subset=[date_column] + price_columns
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

            fig = create_underlying_performance_chart(
                rebased_df,
                date_column,
                price_columns
            )

            st.pyplot(fig)

        else:
            st.warning("Please select at least one underlying.")

        st.write("Selected inputs:")

        st.json({
            "product_type": product_type,
            "tenor_years": tenor_years,
            "observation_frequency": observation_frequency,
            "first_call_month": first_call_month,
            "autocall_trigger": autocall_trigger,
            "step_down_size": step_down_size,
            "income_trigger": income_trigger,
            "memory_coupon": memory_coupon,
            "coupon_pa": coupon_pa,
            "capital_barrier": capital_barrier,
            "notional": notional,
            "date_column": date_column,
            "price_columns": price_columns
        })

        st.success("Backtest completed successfully.")

else:
    st.info("Please upload a CSV or Excel file to begin.")
