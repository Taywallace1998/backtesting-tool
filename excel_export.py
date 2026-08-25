from io import BytesIO
import pandas as pd

from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Font
from openpyxl.chart.label import DataLabelList


def create_excel_export(
    product_type,
    tenor_months,
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
    underlying_performance_data=None
):
    output = BytesIO()

    # =========================
    # Inputs
    # =========================

    inputs_df = pd.DataFrame({
        "Input": [
            "Product Type",
            "Tenor months",
            "Observation Frequency",
            "First Call Month",
            "Autocall Trigger (%)",
            "Step-Down Size (%)",
            "Income Trigger (%)",
            "Memory Coupon",
            "Coupon p.a. (%)",
            "Capital Barrier (%)",
            "Date Column",
            "Underlying Columns"
        ],
        "Value": [
            product_type,
            tenor_months,
            observation_frequency,
            first_call_month,
            autocall_trigger,
            step_down_size,
            income_trigger,
            memory_coupon,
            coupon_pa,
            capital_barrier,
            date_column,
            ", ".join(price_columns)
        ]
    })

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # =========================
        # Core sheets
        # =========================

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

        # =========================
        # Autocall Distribution
        # =========================

        if autocall_summary is not None:

            autocall_export = autocall_summary.copy()

            # Convert percentage strings into real
            # Excel percentage values
            autocall_export["%"] = (
                autocall_export["%"]
                .astype(str)
                .str.replace("%", "", regex=False)
                .astype(float)
                / 100
            )

            # Numeric month values used only by
            # the native Excel chart
            autocall_export["Chart Month"] = (
                autocall_export["Autocall Test"]
                .str.replace(" Months", "", regex=False)
            )

            autocall_export.loc[
                autocall_export["Autocall Test"].isin(
                    ["Autocall Missed", "Total"]
                ),
                "Chart Month"
            ] = None

            autocall_export.to_excel(
                writer,
                sheet_name="Autocall Distribution",
                index=False
            )

        # =========================
        # Phoenix Coupon Analysis
        # =========================

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
        # Underlying Performance Data
        # =========================

        if underlying_performance_data is not None:

            performance_export = (
                underlying_performance_data.copy()
            )

            # Convert rebased index values into return %
            # 100 = 0%, 150 = 50%, etc.
            for col in price_columns:
                if col in performance_export.columns:
                    performance_export[col] = (
                        performance_export[col] - 100
                    )

            performance_export.to_excel(
                writer,
                sheet_name="Underlying Performance Data",
                index=False
            )

        # =========================
        # Workbook formatting
        # =========================

        workbook = writer.book

        if "Autocall Distribution" in workbook.sheetnames:

            autocall_sheet = workbook[
                "Autocall Distribution"
            ]

            # Format percentage column
            for cell in autocall_sheet["C"][1:]:
                cell.number_format = "0.00%"

            # Hide the Chart Month helper column
            autocall_sheet.column_dimensions["D"].hidden = True

        for worksheet in workbook.worksheets:

            worksheet.sheet_view.showGridLines = False

            if worksheet.max_row >= 1:
                for cell in worksheet[1]:
                    cell.font = Font(
                        bold=True
                    )

        # =========================
        # Charts sheet
        # =========================

        charts_sheet = workbook.create_sheet(
            "Charts"
        )

        charts_sheet.sheet_view.showGridLines = False

        charts_sheet["A1"] = " "

        # =========================
        # Native Excel Autocall Chart
        # =========================

        if (
            autocall_summary is not None
            and "Autocall Distribution" in workbook.sheetnames
        ):

            autocall_sheet = workbook[
                "Autocall Distribution"
            ]

            # Exclude Autocall Missed and Total
            chart_last_row = (
                autocall_sheet.max_row - 2
            )

            if chart_last_row >= 2:

                autocall_chart = BarChart()

                autocall_chart.type = "col"

                autocall_chart.title = (
                    "Autocall Back-Test"
                )

                autocall_chart.height = 12
                autocall_chart.width = 24

                autocall_chart.legend = None

                autocall_chart.x_axis.title = (
                    "Observation Point in Months from Strike"
                )

                autocall_chart.y_axis.title = ""

                autocall_chart.y_axis.numFmt = "0.00%"

                autocall_chart.y_axis.scaling.min = 0

                # Percentage data from column C
                data = Reference(
                    autocall_sheet,
                    min_col=3,
                    min_row=1,
                    max_row=chart_last_row
                )

                # Numeric months from hidden column D
                categories = Reference(
                    autocall_sheet,
                    min_col=4,
                    min_row=2,
                    max_row=chart_last_row
                )

                autocall_chart.add_data(
                    data,
                    titles_from_data=True
                )

                autocall_chart.set_categories(
                    categories
                )

                # Match Streamlit blue bars
                series = autocall_chart.series[0]

                series.graphicalProperties.solidFill = (
                    "2F75B5"
                )

                series.graphicalProperties.line.solidFill = (
                    "2F75B5"
                )

                # Narrower bars
                autocall_chart.gapWidth = 180

                # Percentage labels above bars
                autocall_chart.dLbls = DataLabelList()

                autocall_chart.dLbls.showVal = True

                autocall_chart.dLbls.numFmt = "0.00%"

                autocall_chart.dLbls.position = "outEnd"

                charts_sheet.add_chart(
                    autocall_chart,
                    "A3"
                )

        # =========================
        # Native Excel Underlying Chart
        # =========================

        if (
            underlying_performance_data is not None
            and "Underlying Performance Data"
            in workbook.sheetnames
        ):

            performance_sheet = workbook[
                "Underlying Performance Data"
            ]

            if (
                performance_sheet.max_row >= 2
                and performance_sheet.max_column >= 2
            ):

                underlying_chart = LineChart()

                underlying_chart.title = ""

                underlying_chart.height = 14
                underlying_chart.width = 24

                underlying_chart.legend.position = "t"

                underlying_chart.y_axis.title = ""
                underlying_chart.x_axis.title = ""

                underlying_chart.y_axis.numFmt = '0"%"'

                # Let Excel dynamically scale
                underlying_chart.y_axis.scaling.min = None
                underlying_chart.y_axis.scaling.max = None

                data = Reference(
                    performance_sheet,
                    min_col=2,
                    min_row=1,
                    max_col=performance_sheet.max_column,
                    max_row=performance_sheet.max_row
                )

                dates = Reference(
                    performance_sheet,
                    min_col=1,
                    min_row=2,
                    max_row=performance_sheet.max_row
                )

                underlying_chart.add_data(
                    data,
                    titles_from_data=True,
                    from_rows=False
                )

                underlying_chart.set_categories(
                    dates
                )

                # Match Streamlit chart colours
                line_colours = [
                    "548235",  # green
                    "FF5B57",  # red
                    "F4B183",  # orange
                    "1F3A93",  # navy
                    "70AD47"
                ]

                for i, series in enumerate(
                    underlying_chart.series
                ):

                    colour = line_colours[
                        i % len(line_colours)
                    ]

                    series.graphicalProperties.line.solidFill = (
                        colour
                    )

                    series.graphicalProperties.line.width = (
                        18000
                    )

                    series.marker.symbol = "none"

                underlying_chart.x_axis.number_format = (
                    "dd/mm/yy"
                )

                charts_sheet.add_chart(
                    underlying_chart,
                    "A28"
                )

        # =========================
        # Basic column widths
        # =========================

        for sheet_name in [
            "Inputs",
            "Summary",
            "Autocall Distribution",
            "Phoenix Coupon Analysis"
        ]:

            if sheet_name in workbook.sheetnames:

                ws = workbook[sheet_name]

                for column_cells in ws.columns:

                    max_length = 0

                    column_letter = (
                        column_cells[0].column_letter
                    )

                    for cell in column_cells:

                        try:
                            if cell.value is not None:
                                max_length = max(
                                    max_length,
                                    len(str(cell.value))
                                )
                        except Exception:
                            pass

                    ws.column_dimensions[
                        column_letter
                    ].width = min(
                        max_length + 2,
                        35
                    )

        # =========================
        # Underlying data date format
        # =========================

        if (
            "Underlying Performance Data"
            in workbook.sheetnames
        ):

            performance_sheet = workbook[
                "Underlying Performance Data"
            ]

            for cell in performance_sheet["A"][1:]:
                cell.number_format = "dd/mm/yyyy"

    output.seek(0)

    return output
