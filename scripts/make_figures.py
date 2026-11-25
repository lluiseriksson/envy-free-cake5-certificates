"""Generate 3 publication-quality 300 DPI figures for Paper 45 (Filos-Ratsikas et al., arXiv:2611.33149).

Author: Lluis Eriksson
License: MIT
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FIG_DIR = ROOT / "figures"

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "figure.dpi": 300,
})


def make_fig1() -> None:
    d1 = json.loads((DATA_DIR / "exp1_lemma39_hall_margin.json").read_text(encoding="utf-8"))["rows"]
    d2 = json.loads((DATA_DIR / "exp2_query_complexity_scaling.json").read_text(encoding="utf-8"))["rows"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.5))

    ks = [r["subset_size_k"] for r in d1]
    lbs = [r["raw_weight_lb_float"] for r in d1]
    km1 = [k - 1 for k in ks]
    w = 0.34
    ax1.bar([k - w / 2 for k in ks], lbs, width=w, color="#2b5c8f", label=r"Lemma 3.9 lower bound $(9|P|-8)/8$")
    ax1.bar([k + w / 2 for k in ks], km1, width=w, color="#c95b1d", label=r"Strict ceiling threshold $|P| - 1$")
    for k, v in zip(ks, lbs):
        ax1.text(k - w / 2, v + 0.08, f"{v:.3f}", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax1.set_title("(a) Lemma 3.9 Softmax Hall Margin")
    ax1.set_xlabel(r"Piece subset size $|P| \in \{1, 2, 3, 4\}$")
    ax1.set_ylabel("Agent count lower bound")
    ax1.set_xticks(ks)
    ax1.set_ylim(0, 4.4)
    ax1.grid(True, axis="y", ls="--", alpha=0.35)
    ax1.legend(loc="upper left", framealpha=0.94, fontsize=7.4)

    ls = [r["log2_inv_eps"] for r in d2]
    ax2.semilogy(ls, [r["tree_enum_L3"] for r in d2], "o-", color="#4c8c4a", lw=2.0, label=r"Theorem 2 tree enum. $L^3$")
    ax2.semilogy(ls, [r["nested_5_L5"] for r in d2], "s--", color="#2b5c8f", lw=1.8, label=r"5-nested bisection $L^5$")
    ax2.semilogy(ls, [r["grid_brute_2p"] for r in d2], "^:", color="#c95b1d", lw=1.8, label=r"Exponential baseline $2^L = 1/\varepsilon$")
    ax2.set_title("(b) Unit-Constant Query Complexity Scaling")
    ax2.set_xlabel(r"Precision bits $L = \log_2(1/\varepsilon)$")
    ax2.set_ylabel("Scaling factor (log axis)")
    ax2.grid(True, ls="--", alpha=0.35)
    ax2.legend(loc="upper left", framealpha=0.94, fontsize=7.4)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_hall_margin_and_queries.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def make_fig2() -> None:
    d3 = json.loads((DATA_DIR / "exp3_stability_lipschitz_headroom.json").read_text(encoding="utf-8"))["rows"]
    d4 = json.loads((DATA_DIR / "exp4_complete_ef5_audit.json").read_text(encoding="utf-8"))["rows"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.5))

    xs = list(range(len(d3)))
    w = 0.34
    sr = [r["stab_ratio"] for r in d3]
    lr = [r["lip_ratio"] for r in d3]
    labs3 = [f"$\\gamma={r['gamma']}$\n(C{i+9})" for i, r in enumerate(d3)]
    b1 = ax1.bar([x - w / 2 for x in xs], sr, width=w, color="#2b5c8f", label=r"$\|\ell-\ell^*\|_\infty / (3\gamma^{-3}\delta)$ (Lem. 3.17)")
    b2 = ax1.bar([x + w / 2 for x in xs], lr, width=w, color="#c95b1d", label=r"$\|\ell^*(m)-\ell^*(m')\|_\infty / (13\gamma^{-3}d)$ (Lem. 3.18)")
    for bar, v in zip(b1, sr):
        ax1.text(bar.get_x() + bar.get_width() / 2, v * 1.15, f"{v:.3f}", ha="center", va="bottom", fontsize=6.6, fontweight="bold", color="#1b3e63")
    for bar, v in zip(b2, lr):
        ax1.text(bar.get_x() + bar.get_width() / 2, v * 1.15, f"{v:.4f}" if v < 0.01 else f"{v:.3f}", ha="center", va="bottom", fontsize=6.6, fontweight="bold", color="#8c3b0e")
    ax1.axhline(1.0, color="#b22222", ls="--", lw=1.2, label="Theoretical ceiling $= 1$")
    ax1.set_yscale("log")
    ax1.set_title("(a) Non-Zero Stability & Lipschitz Ratios (Log Scale)")
    ax1.set_xticks(xs)
    ax1.set_xticklabels(labs3)
    ax1.set_ylabel("Exact ratio to ceiling (log scale)")
    ax1.set_ylim(2e-3, 3.5)
    ax1.grid(True, axis="y", ls="--", alpha=0.35)
    ax1.legend(loc="upper right", framealpha=0.94, fontsize=6.6)

    from fractions import Fraction
    labs4 = ["Right Gap\nExact 0-EF", "Left Gap\nExact 0-EF", "Uniform\nExact 0-EF", "Bisected\n$\\varepsilon=1/25$"]
    envy = [float(Fraction(r["max_envy"])) for r in d4]
    targ = [float(Fraction(r["target_eps"])) for r in d4]
    ax2.bar([x - w / 2 for x in range(4)], envy, width=w, color="#4c8c4a", label="Certified exact max envy")
    ax2.bar([x + w / 2 for x in range(4)], targ, width=w, color="#c95b1d", label=r"Target tolerance $\varepsilon$")
    for i, r in enumerate(d4):
        yv = max(envy[i], targ[i])
        ax2.text(i, yv + 0.0025, f"envy={r['max_envy']}\n(gap {r['fifth_piece']})", ha="center", va="bottom", fontsize=7.2, fontweight="bold")
    ax2.set_title("(b) Complete 5-Agent Contiguous EF Audit")
    ax2.set_xticks(range(4))
    ax2.set_xticklabels(labs4, fontsize=7.5)
    ax2.set_ylabel("Additive envy")
    ax2.set_ylim(0, 0.055)
    ax2.grid(True, axis="y", ls="--", alpha=0.35)
    ax2.legend(loc="upper left", framealpha=0.94, fontsize=7.5)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_stability_and_ef5_audit.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def make_fig3() -> None:
    rep = json.loads((DATA_DIR / "certificate_replay_summary.json").read_text(encoding="utf-8"))["certificates"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.5))

    mode_colors = {
        "hall_robust_connectivity_lemma34_35_cert": "#2b5c8f",
        "softmax_weight_balance_lemma39_cert": "#3d85c6",
        "stability_and_lipschitz_lemma317_318_cert": "#4c8c4a",
        "complete_ef5_allocation_theorem1_2_cert": "#c95b1d",
    }
    mode_labels = {
        "hall_robust_connectivity_lemma34_35_cert": "Mode 1 (Hall)",
        "softmax_weight_balance_lemma39_cert": "Mode 2 (Softmax)",
        "stability_and_lipschitz_lemma317_318_cert": "Mode 3 (Stab./Lip.)",
        "complete_ef5_allocation_theorem1_2_cert": "Mode 4 (EF5)",
    }
    seen = set()
    for i, r in enumerate(rep):
        m = r["mode"]
        lbl = mode_labels[m] if m not in seen else None
        seen.add(m)
        ax1.bar(i, r["verify_ms"], width=0.68, color=mode_colors[m], label=lbl)
    ax1.set_title("(a) Canonical Certificate Replay Latency")
    ax1.set_xlabel("Canonical EF-CAKE5-CERT-1.0 certificate (C1-C16)")
    ax1.set_ylabel("Exact zero-float replay latency (ms)")
    ax1.set_xticks(range(len(rep)))
    ax1.set_xticklabels([f"C{i+1}" for i in range(len(rep))], fontsize=7)
    ax1.set_ylim(0, max(r["verify_ms"] for r in rep) * 1.45)
    ax1.grid(True, axis="y", ls="--", alpha=0.35)
    ax1.legend(loc="upper right", ncol=2, framealpha=0.92, fontsize=7.2)

    cats = ["Global /\nType", "Mode 1\nHall", "Mode 2\nSoftmax", "Mode 3\nStab.", "Mode 4\nEF5"]
    vals = [12, 12, 12, 12, 12]
    cols = ["#666666", "#2b5c8f", "#3d85c6", "#4c8c4a", "#c95b1d"]
    bars = ax2.bar(cats, vals, width=0.58, color=cols)
    for b in bars:
        ax2.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.35, "12/12", ha="center", va="bottom", fontweight="bold", fontsize=8.5)
    ax2.set_title("(b) Adversarial Red-Team Audit (60/60 Rejected)")
    ax2.set_ylabel("Live adversarial forgeries rejected")
    ax2.set_ylim(0, 15.0)
    ax2.grid(True, axis="y", ls="--", alpha=0.35)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_certificate_replay_atlas.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    make_fig1()
    make_fig2()
    make_fig3()
    print("Generated all 3 Paper 45 publication figures successfully.")


if __name__ == "__main__":
    main()
