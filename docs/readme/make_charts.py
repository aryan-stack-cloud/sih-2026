"""Regenerate the light/dark README result charts from saved measurements.

Run from any directory with: python docs/readme/make_charts.py
Requires matplotlib. Output is intentionally fixed at 1600 px width (200 dpi).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import PercentFormatter


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCENARIOS = "ABCDEFG"
SCENARIO_NAMES = (
    "A Mostly Fixed  ·  B Mostly Periodic  ·  C Frequency-Agile  ·  D Mixed\n"
    "E High-Density  ·  F Sparse  ·  G Rapidly Changing"
)


@dataclass(frozen=True)
class Policy:
    key: str
    name: str
    family: str


POLICIES = (
    Policy("baseline", "Fixed sweep", "Reference"),
    Policy("random", "Random", "Reference"),
    Policy("ctmc", "CTMC floor", "Designed"),
    Policy("index", "Index", "Designed"),
    Policy("bandit", "Bandit", "Learned"),
    Policy("q_learning", "Q-learning", "Learned"),
    Policy("dqn", "DQN", "Learned"),
    Policy("ppo", "PPO", "Learned"),
)
BY_KEY = {policy.key: policy for policy in POLICIES}

THEMES = {
    "light": {
        "surface": "#ffffff", "ink": "#0b0b0b", "secondary": "#52514e",
        "muted": "#676660", "grid": "#e1e0d9", "axis": "#c3c2b7",
        "Reference": "#2a78d6", "Designed": "#eb6834", "Learned": "#1baf7a",
        "ramp": ("#cde2fb", "#86b6ef", "#3987e5", "#184f95", "#0d366b"),
    },
    "dark": {
        "surface": "#0d1117", "ink": "#ffffff", "secondary": "#c3c2b7",
        "muted": "#a5a49d", "grid": "#2c2c2a", "axis": "#383835",
        "Reference": "#3987e5", "Designed": "#d95926", "Learned": "#199e70",
        "ramp": ("#184f95", "#256abf", "#3987e5", "#86b6ef", "#cde2fb"),
    },
}


def read_scenarios() -> dict[str, dict]:
    directory = ROOT / "sih" / "audit-results"
    data = {scenario: json.loads((directory / f"results_{scenario}.json").read_text(encoding="utf-8-sig"))
            for scenario in SCENARIOS}
    for scenario, result in data.items():
        if result["scenario"] != scenario or len(result["seeds"]) != 10:
            raise ValueError(f"Unexpected scenario or seed count in results_{scenario}.json")
        for policy in POLICIES:
            for measure in ("pd", "run_intercept_rate"):
                value = result["policies"][policy.key][measure]
                if not 0 <= value <= 1:
                    raise ValueError(f"Invalid {measure} for {scenario}/{policy.key}: {value}")
    return data


def setup(theme: dict) -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9,
        "text.color": theme["ink"], "axes.labelcolor": theme["ink"],
        "xtick.color": theme["secondary"], "ytick.color": theme["secondary"],
        "axes.edgecolor": theme["axis"], "axes.linewidth": 0.6,
        "figure.facecolor": theme["surface"], "axes.facecolor": theme["surface"],
        "savefig.facecolor": theme["surface"], "savefig.edgecolor": theme["surface"],
    })


def save(fig: plt.Figure, name: str, variant: str) -> None:
    output = HERE / f"{name}-{variant}.png"
    fig.savefig(output, dpi=200, metadata={"Software": "matplotlib"})
    plt.close(fig)
    print(f"{output.name}: {output.stat().st_size:,} bytes")


def contrast_ink(color: tuple[float, float, float]) -> str:
    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
    luminance = sum(weight * linear(component) for weight, component in zip((0.2126, 0.7152, 0.0722), color))
    return "#0b0b0b" if luminance > 0.18 else "#ffffff"


def draw_heatmap(data: dict[str, dict], variant: str) -> None:
    theme = THEMES[variant]
    setup(theme)
    fig, ax = plt.subplots(figsize=(8, 5.25), dpi=200)
    fig.subplots_adjust(left=0.075, right=0.96, top=0.75, bottom=0.11)
    fig.text(0.075, 0.945, "Detection rate across scenarios", fontsize=16, weight="bold", color=theme["ink"])
    fig.text(0.075, 0.902, "10 seeds per scenario · 2,000 steps per episode · cell values are detection rates",
             fontsize=8.8, color=theme["secondary"])
    fig.text(0.075, 0.855, SCENARIO_NAMES, fontsize=8.0, linespacing=1.7,
             va="top", color=theme["secondary"])

    values = [[data[s]["policies"][p.key]["pd"] for s in SCENARIOS] for p in POLICIES]
    ramp = LinearSegmentedColormap.from_list("pd-blue", theme["ramp"])
    maximum = 0.40  # fixed across both themes and all seven scenarios
    for row, policy in enumerate(POLICIES):
        ax.text(-0.15, row + 0.5, policy.name, ha="right", va="center", fontsize=9.4,
                weight="bold" if policy.key == "baseline" else "normal", color=theme["ink"])
        for col, value in enumerate(values[row]):
            color = ramp(min(value / maximum, 1))
            ax.add_patch(Rectangle((col + 0.04, row + 0.07), 0.92, 0.86,
                                   facecolor=color, edgecolor="none"))
            ax.text(col + 0.5, row + 0.5, f"{value:.1%}", ha="center", va="center",
                    fontsize=9.4, weight="normal", color=contrast_ink(color[:3]))
    for y in (2, 4):
        ax.hlines(y, 0, 7, color=theme["axis"], lw=0.65)
    for label, y in (("REFERENCE", 0.5), ("DESIGNED", 2.5), ("LEARNED", 4.5)):
        ax.text(-2.55, y, label, ha="left", va="center", fontsize=7.9,
                weight="bold", color=theme["secondary"])
    for col, scenario in enumerate(SCENARIOS):
        ax.text(col + 0.5, -0.43, scenario, ha="center", va="center", fontsize=10,
                weight="bold", color=theme["ink"])
    ax.set_xlim(-2.6, 7.0)
    ax.set_ylim(8.0, -0.75)
    ax.axis("off")
    fig.text(0.075, 0.045, "Source: synthetic A–G audit results · Pd = detections / active scan opportunities",
             fontsize=8.0, color=theme["secondary"])
    save(fig, "pd-heatmap", variant)


def family_legend(theme: dict) -> list[Line2D]:
    return [Line2D([0], [0], marker="o", linestyle="", markerfacecolor=theme[family],
                   markeredgecolor=theme["surface"], markeredgewidth=1.1,
                   markersize=8, label=family)
            for family in ("Reference", "Designed", "Learned")]


def draw_tradeoff(data: dict[str, dict], variant: str) -> None:
    theme = THEMES[variant]
    setup(theme)
    fig, ax = plt.subplots(figsize=(8, 5.05), dpi=200)
    fig.subplots_adjust(left=0.15, right=0.94, top=0.77, bottom=0.19)
    fig.text(0.075, 0.945, "Detection rate vs burst coverage", fontsize=16, weight="bold", color=theme["ink"])
    fig.text(0.075, 0.898, "Mean over scenarios A–G · 10 seeds per scenario · 2,000 steps per episode",
             fontsize=8.8, color=theme["secondary"])
    fig.legend(handles=family_legend(theme), loc="upper left", bbox_to_anchor=(0.075, 0.856),
               ncol=3, frameon=False, columnspacing=1.5, handletextpad=0.3,
               labelcolor=theme["ink"], fontsize=8.7)

    offsets = {
        "baseline": (12, -12), "random": (-28, 20), "ctmc": (15, -22),
        "index": (-13, 14), "bandit": (10, -16), "q_learning": (13, 10),
        "dqn": (13, -16), "ppo": (12, 12),
    }
    for policy in POLICIES:
        x = sum(data[s]["policies"][policy.key]["run_intercept_rate"] for s in SCENARIOS) / 7
        y = sum(data[s]["policies"][policy.key]["pd"] for s in SCENARIOS) / 7
        ax.scatter(x, y, s=112 if policy.key == "baseline" else 65,
                   facecolor=theme[policy.family], edgecolor=theme["surface"],
                   linewidth=1.5, zorder=4)
        dx, dy = offsets[policy.key]
        ax.annotate(policy.name, xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                    fontsize=9.2, weight="bold" if policy.key == "baseline" else "normal",
                    color=theme["ink"], ha="left" if dx >= 0 else "right", va="center",
                    arrowprops={"arrowstyle": "-", "color": theme["muted"], "lw": 0.55,
                                "shrinkA": 3, "shrinkB": 6})
    ax.set_xlim(0.18, 0.385)
    ax.set_ylim(0.052, 0.217)
    ax.set_xticks([0.20, 0.25, 0.30, 0.35])
    ax.set_yticks([0.06, 0.10, 0.14, 0.18])
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_xlabel("Share of distinct bursts caught", labelpad=10, fontsize=9.8)
    ax.set_ylabel("Detection rate (Pd)", labelpad=10, fontsize=9.8)
    ax.grid(axis="both", color=theme["grid"], linewidth=0.55)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=0, labelsize=8.6, pad=6)
    fig.text(0.075, 0.052, "Each dot is one policy · higher is better on both axes · Fixed sweep shown larger",
             fontsize=8, color=theme["secondary"])
    save(fig, "tradeoff", variant)


def draw_real_data(variant: str) -> None:
    theme = THEMES[variant]
    setup(theme)
    replay = json.loads((HERE / "turing_results.json").read_text(encoding="utf-8"))["policies"]
    ordered = sorted(replay, key=lambda key: (-replay[key]["pd"], -replay[key]["scan_efficiency"], key))
    fig, axes = plt.subplots(1, 2, figsize=(8, 5.05), dpi=200)
    fig.subplots_adjust(left=0.205, right=0.97, top=0.68, bottom=0.17, wspace=0.19)
    fig.text(0.075, 0.945, "Radar replay: listening pays off", fontsize=16, weight="bold", color=theme["ink"])
    fig.text(0.075, 0.895, "Turing Synthetic Radar Dataset · 50 held-out scan-mode files × 1,000 steps",
             fontsize=8.8, color=theme["secondary"])
    fig.text(0.075, 0.861, "Learned models trained on 150 files × 1,000 steps", fontsize=8.5,
             color=theme["secondary"])
    fig.legend(handles=family_legend(theme), loc="upper left", bbox_to_anchor=(0.075, 0.825),
               ncol=3, frameon=False, columnspacing=1.5, handletextpad=0.3,
               labelcolor=theme["ink"], fontsize=8.7)
    for ax, (measure, title, limit, ticks) in zip(axes, (
        ("pd", "Detection rate (Pd)", 37, [0, 10, 20, 30]),
        ("scan_efficiency", "Scan efficiency", 75, [0, 20, 40, 60]),
    )):
        for row, key in enumerate(ordered):
            policy = BY_KEY[key]
            value = replay[key][measure]
            ax.barh(row, value, height=0.18, color=theme[policy.family], edgecolor="none", zorder=3)
            ax.text(value + limit * 0.025, row, f"{value:.1f}%", va="center", ha="left",
                    fontsize=8.8, color=theme["ink"])
        ax.set_xlim(0, limit)
        ax.set_ylim(len(ordered) - 0.45, -0.55)
        ax.set_title(title, loc="left", fontsize=10.1, weight="bold", color=theme["ink"], pad=13)
        ax.set_xticks(ticks, [f"{tick}%" for tick in ticks])
        ax.grid(axis="x", color=theme["grid"], linewidth=0.55)
        ax.set_axisbelow(True)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="both", length=0, labelsize=8.8, pad=7)
    axes[0].set_yticks(range(len(ordered)), [BY_KEY[key].name for key in ordered])
    axes[1].set_yticks(range(len(ordered)), [])
    axes[0].tick_params(axis="y", labelsize=9.3)
    axes[0].set_xlabel("Percent of active opportunities detected", fontsize=8,
                       color=theme["secondary"], labelpad=20)
    axes[1].set_xlabel("Percent of scans on active bands", fontsize=8,
                       color=theme["secondary"], labelpad=20)
    save(fig, "real-data", variant)


def main() -> None:
    data = read_scenarios()
    for variant in ("light", "dark"):
        draw_heatmap(data, variant)
        draw_tradeoff(data, variant)
        draw_real_data(variant)


if __name__ == "__main__":
    main()
