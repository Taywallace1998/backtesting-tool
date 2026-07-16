from io import BytesIO
import pandas as pd
from openpyxl.drawing.image import Image


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
    autocall_summary=None,
    underlying_performance_fig=None,
    autocall_distribution_fig=None
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

        if product_type in [
            "Phoenix Autocall",
            "Step-Down Phoenix Autocall"
        ]:
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

        # =========================
        # Charts sheet
        # =========================

        workbook = writer.book
        charts_sheet = workbook.create_sheet("Charts")

        charts_sheet["A1"] = "Autocall Backtest Charts"
        from openpyxl.styles import Font
        charts_sheet["A1"].font = Font(
            bold=True,
            size=16
        )

        image_buffers = []

        if autocall_distribution_fig is not None:
            autocall_buffer = BytesIO()

            autocall_distribution_fig.savefig(
                autocall_buffer,
                format="png",
                dpi=150,
                bbox_inches="tight"
            )

            autocall_buffer.seek(0)
            image_buffers.append(autocall_buffer)

            autocall_image = Image(autocall_buffer)
            autocall_image.width = 900
            autocall_image.height = 450

            charts_sheet.add_image(
                autocall_image,
                "A3"
            )

        if underlying_performance_fig is not None:
            underlying_buffer = BytesIO()

            underlying_performance_fig.savefig(
                underlying_buffer,
                format="png",
                dpi=150,
                bbox_inches="tight"
            )

            underlying_buffer.seek(0)
            image_buffers.append(underlying_buffer)

            underlying_image = Image(underlying_buffer)
            underlying_image.width = 900
            underlying_image.height = 450

            charts_sheet.add_image(
                underlying_image,
                "A28"
            )

        charts_sheet.sheet_view.showGridLines = False


    output.seek(0)

    return output
