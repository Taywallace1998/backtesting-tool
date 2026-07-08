from io import BytesIO
import pandas as pd


def create_excel_export(
    product_type,
    tenor_years,
    observation_frequency,
    first_call_month,
    autocall_trigger,
    step_down_size,
    income_trigger,
    memory_coupon,
    coupon_pa,
    capital_barrier,
    notional,
    date_column,
    price_columns,
    results,
    summary_stats,
    autocall_summary=None
):
    output = BytesIO()

    inputs_df = pd.DataFrame({
        "Input": [
            "Product Type",
            "Tenor Years",
            "Observation Frequency",
            "First Call Month",
            "Autocall Trigger (%)",
            "Step-Down Size (%)",
            "Income Trigger (%)",
            "Memory Coupon",
            "Coupon p.a. (%)",
            "Capital Barrier (%)",
            "Notional",
            "Date Column",
            "Underlying Columns"
        ],
        "Value": [
            product_type,
            tenor_years,
            observation_frequency,
            first_call_month,
            autocall_trigger,
            step_down_size,
            income_trigger,
            memory_coupon,
            coupon_pa,
            capital_barrier,
            notional,
            date_column,
            ", ".join(price_columns)
        ]
    })

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        inputs_df.to_excel(
            writer,
            sheet_name="Inputs",
            index=False
        )

        results.to_excel(
            writer,
            sheet_name="Backtest Results",
            index=False
        )

        summary_stats.to_excel(
            writer,
            sheet_name="Summary",
            index=False
        )

        if autocall_summary is not None:
            autocall_summary.to_excel(
                writer,
                sheet_name="Autocall Distribution",
                index=False
            )

        if product_type == "Phoenix Autocall":
            phoenix_columns = [
                col for col in results.columns
                if col in [
                    "Coupon Paid This Observation (%)",
                    "Missed Coupon Bank (%)",
                    "Coupon Paid on Final Observation (%)",
                    "Total Coupons Paid (%)",
                    "Coupons Paid",
                    "Coupon Opportunities Until Exit",
                    "Coupon Capture Rate (%)"
                ]
            ]

            if phoenix_columns:
                results[phoenix_columns].to_excel(
                    writer,
                    sheet_name="Phoenix Coupon Analysis",
                    index=False
                )

    output.seek(0)

    return output
