"""Skapa figurer direkt från data/attendance.csv, utan att läsa PDF:erna igen."""

from pathlib import Path
from textwrap import fill
from typing import Any

import matplotlib

# Figurerna sparas till filer och behöver inget grafiskt fönster.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter
import pandas as pd

from .io import read_dataframe, read_json


# Färgunderlag: https://everydayapps.se/app/sverigespartier/kallor
# V är mörkrött enligt önskemål, SD använder den konventionella gula färgen.
# Detta är en diagrampalett, inte en exakt återgivning av alla aktuella varumärkesprofiler.
PARTY_COLORS = {
    "Vänsterpartiet": "#A6192E",
    "Arbetarepartiet Socialdemokraterna": "#ED1B34",
    "Miljöpartiet De Gröna": "#1F833C",
    "Centerpartiet": "#114838",
    "Liberalerna": "#006AB3",
    "Moderaterna": "#0D9DDB",
    "Sverigedemokraterna": "#DDDD00",
    "Kristdemokraterna": "#005EA1",
}

PARTY_LABELS = {
    "Vänsterpartiet": "V",
    "Arbetarepartiet Socialdemokraterna": "S",
    "Miljöpartiet De Gröna": "MP",
    "Centerpartiet": "C",
    "Liberalerna": "L",
    "Moderaterna": "M",
    "Sverigedemokraterna": "SD",
    "Kristdemokraterna": "KD",
}

STATUSES = ["present", "absent_with_replacement", "absent_without_replacement"]


def make_plot_footer(analysis_summary: dict[str, Any]) -> str:
    """Beskriv urval, bortvalda personer och orsaker till oanalyserade möten."""
    excluded = [
        f"{person['name']} ({PARTY_LABELS.get(person['party'], person['party'])})"
        for person in analysis_summary["excluded_members"]
    ]
    skipped = [f"{meeting['date']}: {meeting['reason'].lower()}" for meeting in analysis_summary["skipped_meetings"]]
    paragraphs = [
        f"Analyserade möten: {analysis_summary['analyzed_meetings']} av {analysis_summary['total_meetings']} kända möten "
        f"under mandatperioden {analysis_summary['term_start']}–{analysis_summary['term_end']}, t.o.m. {analysis_summary['as_of']}.",
        "Urval: nu listade ledamöter vars registrerade uppdrag omfattar mandatperiodens start. Partistaplarna gäller endast detta urval.",
        "Bortvalda (uppdraget omfattar inte starten eller startdatum saknas): " + (", ".join(excluded) or "inga") + ".",
        "Ej analyserade möten: " + ("; ".join(skipped) or "inga") + ".",
        "Källa: data/attendance.csv och data/analysis_summary.json. Del av paragraf räknas som hela. Historiskt avgångna ledamöter återställs inte av urvalet.",
    ]
    return "\n".join(fill(paragraph, width=145) for paragraph in paragraphs)


def summarize_attendance(attendance_df: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    """Räkna andelar av ledamot–paragraf-rader, inte andelar av möten."""
    if attendance_df.empty:
        raise ValueError("Närvarotabellen är tom")
    if attendance_df[group_columns + ["status"]].isna().any().any():
        raise ValueError("Grupp eller status saknas i närvarotabellen")
    if not attendance_df["status"].isin(STATUSES).all():
        raise ValueError("Närvarotabellen innehåller en okänd status")

    counts = attendance_df.groupby(group_columns + ["status"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=STATUSES, fill_value=0)
    percentages = counts.div(counts.sum(axis=1), axis=0) * 100
    percentages["observations"] = counts.sum(axis=1)
    return percentages.reset_index()


def summarize_meeting_attendance(
    attendance_df: pd.DataFrame, group_columns: list[str], presence_first: bool = True,
) -> pd.DataFrame:
    """Räkna varje ledamot en gång per möte och kategori, oavsett antal paragrafer."""
    if attendance_df.empty or not attendance_df["status"].isin(STATUSES).all():
        raise ValueError("Närvarotabellen är tom eller innehåller okänd status")
    keys = ["date", "representative_id", "member", "party"]
    if attendance_df[keys].isna().any().any():
        raise ValueError("Datum eller personuppgifter saknas")
    rows = attendance_df[keys].copy()
    rows["date"] = pd.to_datetime(rows["date"]).dt.normalize()
    rows["present"] = attendance_df["status"].eq("present")
    rows["absent_with_replacement"] = attendance_df["status"].eq("absent_with_replacement")
    meetings = rows.groupby(keys)[["present", "absent_with_replacement"]].any().reset_index()
    if presence_first:
        meetings["absent_with_replacement"] &= ~meetings["present"]
    meetings["absent_without_replacement"] = ~(
        meetings["present"] | meetings["absent_with_replacement"]
    )
    groups = meetings.groupby(group_columns)
    percentages = groups[STATUSES].mean() * 100
    percentages["observations"] = groups.size()
    return percentages.reset_index()


def save_attendance_plot(
    summary: pd.DataFrame,
    labels: list[str],
    title: str,
    subtitle: str,
    output_path: Path,
    footer: str,
    per_meeting: bool = False,
) -> None:
    """Spara staplar; möteskategorier kan överlappa och summera till mer än 100 %."""
    colors = [PARTY_COLORS.get(party, "#777777") for party in summary["party"]]
    darker_colors = [tuple(component * 0.55 for component in to_rgb(color)) for color in colors]
    positions = range(len(summary))
    footer_height = len(footer.splitlines()) * 0.16 + 0.35
    figure_height = max(5, len(summary) * 0.34 + 2) + footer_height
    fig, ax = plt.subplots(figsize=(13, figure_height))

    ax.barh(positions, summary["present"], color=colors, height=0.72)
    ax.barh(
        positions, summary["absent_with_replacement"], left=summary["present"],
        color=darker_colors, height=0.72, hatch="///", edgecolor="white", linewidth=0.3,
    )
    ax.barh(
        positions, summary["absent_without_replacement"],
        left=summary["present"] + summary["absent_with_replacement"],
        color="#E1E4E8", height=0.72,
    )
    maximum = max(100, float(summary[STATUSES].sum(axis=1).max())) if per_meeting else 100
    for position, value in enumerate(summary["present"]):
        ax.text(maximum + 1, position, f"{value:.1f} %", va="center", fontsize=9)

    ax.set_yticks(list(positions), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, maximum + 12)
    ax.set_xticks(list(range(0, int(maximum) + 1, 20)))
    if maximum > 100:
        ax.axvline(100, color="#888888", linestyle=":", linewidth=0.8)
    ax.xaxis.set_major_formatter(PercentFormatter())
    unit = "ledamot–möten" if per_meeting else "ledamot–paragraf-rader"
    ax.set_xlabel(f"Andel registrerade {unit} · siffran till höger visar egen närvaro")
    ax.set_title(f"{title}\n{subtitle}", loc="left", pad=55, fontsize=13)
    ax.set_axisbelow(True)
    ax.grid(axis="x", alpha=0.2)
    ax.tick_params(axis="y", length=0, labelsize=9)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(handles=[
        Patch(facecolor="#888888", label="Närvarande · partifärg"),
        Patch(facecolor="#444444", hatch="///", edgecolor="white", label=("Ersatt under mötet · mörkare" if per_meeting else "Frånvarande med ersättare · mörkare")),
        Patch(facecolor="#E1E4E8", label="Frånvarande utan ersättare"),
    ], loc="lower left", bbox_to_anchor=(0, 1.01), ncol=3, frameon=False, fontsize=9)
    fig.text(
        0.02, 0.01,
        footer,
        fontsize=9, color="#555555",
    )
    fig.tight_layout(rect=(0, footer_height / figure_height, 1, 1))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path.with_suffix(".png"), dpi=180, bbox_inches="tight")
    fig.savefig(output_path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def create_attendance_plots(
    attendance_df: pd.DataFrame, analysis_summary: dict[str, Any],
    output_dir: Path = Path("data/plots"), per_meeting: bool = False,
    presence_first: bool = True,
) -> None:
    """Spara staplade PNG- och SVG-diagram per ledamot och parti från närvarotabellen."""
    if per_meeting:
        members = summarize_meeting_attendance(attendance_df, ["representative_id", "member", "party"], presence_first)
        parties = summarize_meeting_attendance(attendance_df, ["party"], presence_first)
    else:
        members = summarize_attendance(attendance_df, ["representative_id", "member", "party"])
        parties = summarize_attendance(attendance_df, ["party"])
    party_order = {party: index for index, party in enumerate(PARTY_COLORS)}
    members["party_order"] = members["party"].map(party_order).fillna(len(party_order))
    parties["party_order"] = parties["party"].map(party_order).fillna(len(party_order))
    members = members.sort_values(["party_order", "present", "member"], ascending=[True, False, True])
    parties = parties.sort_values("party_order")
    dates = pd.to_datetime(attendance_df["date"])
    subtitle = (f"{dates.min():%Y-%m-%d} – {dates.max():%Y-%m-%d} · "
                f"{analysis_summary['analyzed_meetings']} av {analysis_summary['total_meetings']} möten analyserade")
    footer = make_plot_footer(analysis_summary)
    if per_meeting:
        rule = ("Egen närvaro har företräde framför ersättning." if presence_first else
                "Båda räknas om de inträffat under samma möte; stapeln kan därför överstiga 100 %.")
        footer += "\n" + fill(
            "Per möte: egen närvaro på minst en punkt respektive ersatt på minst en punkt. " + rule +
            " Grått: varken egen närvaro eller ersättare på någon punkt. Varje ledamot–möte väger lika.", width=145)

    member_labels = [
        f"{row.member} ({PARTY_LABELS.get(row.party, row.party)})"
        for row in members.itertuples()
    ]
    party_labels = [
        f"{PARTY_LABELS.get(row.party, row.party)}  ·  n={row.observations:,}".replace(",", " ")
        for row in parties.itertuples()
    ]
    suffix = "_by_meeting" if per_meeting else ""
    title_suffix = " · per möte" if per_meeting else ""
    save_attendance_plot(members, member_labels, "Registrerad närvaro per ledamot" + title_suffix, subtitle, output_dir / f"attendance_members{suffix}", footer, per_meeting)
    save_attendance_plot(parties, party_labels, "Registrerad närvaro per parti" + title_suffix, subtitle, output_dir / f"attendance_parties{suffix}", footer, per_meeting)


def main() -> None:
    """Läs den sparade närvarotabellen och skapa figurer utan ny datainsamling."""
    attendance_df = read_dataframe(Path("data/attendance.csv"))
    analysis_summary = read_json(Path("data/analysis_summary.json"))
    create_attendance_plots(attendance_df, analysis_summary)
    create_attendance_plots(attendance_df, analysis_summary, per_meeting=True)
    print("Sparade figurer i data/plots (PNG och SVG)")


if __name__ == "__main__":
    main()
