import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def create_underlying_performance_chart(
    rebased_df,
    date_column,
    price_columns
):
    fig, ax = plt.subplots(figsize=(10, 5))

    colours = [
        "#548235",  # green
        "#ff5b57",  # red
        "#f4b183",  # orange
        "#1f3a93",  # navy
        "#70ad47"
    ]

    for i, col in enumerate(price_columns):
        ax.plot(
            rebased_df[date_column],
            rebased_df[col] - 100,
            label=col,
            linewidth=1.0,
            color=colours[i % len(colours)]
        )

    ax.set_ylim(-50, 200)

    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda y, _: f"{y:.0f}%")
    )

    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))

    plt.setp(
        ax.get_xticklabels(),
        rotation=30,
        ha="right"
    )

    ax.grid(
        axis="y",
        linestyle="-",
        linewidth=0.6,
        alpha=0.35
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.spines["left"].set_color("#0070C0")
    ax.spines["bottom"].set_color("#0070C0")

    ax.tick_params(
        axis="both",
        labelsize=9,
        colors="black"
    )

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.15),
        ncol=len(price_columns),
        frameon=False,
        fontsize=9
    )

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("")

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    fig.tight_layout()

    return fig

def create_autocall_distribution_chart(autocall_summary):
    fig, ax = plt.subplots(figsize=(10, 5))

    chart_data = autocall_summary[
        autocall_summary["Autocall Test"] != "Total"
    ].copy()

    x_labels = (
        chart_data["Autocall Test"]
        .str.replace(" Months", "", regex=False)
    )

    y_values = (
        chart_data["%"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .astype(float)
    )

    bars = ax.bar(
        x_labels,
        y_values,
        color="#2F75B5",
        width=0.35
    )

    ax.set_title(
        "Autocall Back-Test",
        fontsize=12,
        pad=12
    )

    ax.set_xlabel("Observation Point in Months from Strike")
    ax.set_ylabel("")

    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda y, _: f"{y:.2f}%")
    )

    ax.grid(
        axis="y",
        linestyle="-",
        linewidth=0.6,
        alpha=0.35
    )

    ax.set_axisbelow(True)

    for bar, value in zip(bars, y_values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.2f}%",
            ha="center",
            va="bottom",
            fontsize=8
        )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.patch.set_facecolor("#E7E6E6")
    ax.set_facecolor("#E7E6E6")

    fig.tight_layout()

    return fig
