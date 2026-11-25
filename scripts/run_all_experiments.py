"""Generate all 16 canonical EF-CAKE5-CERT-1.0 certificates and 4 exact-Q studies
for Paper 45 (Filos-Ratsikas, Hollender, Latifian, & Tyrovolas, arXiv:2611.33149).

Author: Lluis Eriksson
License: MIT
"""
from __future__ import annotations

import json
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cake5_certifier import SCHEMA_VERSION, verify_cake5_certificate_exact
from src.cake5_exact import (
    check_hall_leaving_agent_robustness,
    delta_favourite_graph,
    eval_pw_const_valuation_q,
    format_rat,
    six_pieces_from_anchor,
)

CERT_DIR = ROOT / "certificates"
DATA_DIR = ROOT / "data"


def _fmt_val(bp: Sequence[Fraction], dens: Sequence[Sequence[Fraction]]) -> Dict[str, Any]:
    return {
        "breakpoints": [format_rat(x) for x in bp],
        "densities_5": [[format_rat(d) for d in row] for row in dens],
    }


def _find_spanning_tree(adj: Sequence[Sequence[int]]) -> List[List[int]]:
    """Build an explicit 8-edge spanning tree of the 9-vertex bipartite graph [5] U [4]."""
    g: List[List[int]] = [[] for _ in range(9)]
    for i in range(5):
        for j in adj[i]:
            g[i].append(5 + j)
            g[5 + j].append(i)
    seen = {0}
    stack = [0]
    edges: List[List[int]] = []
    while stack:
        u = stack.pop()
        for w in g[u]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
                if u < 5:
                    edges.append([u, w - 5])
                else:
                    edges.append([w, u - 5])
    assert len(edges) == 8, f"Expected 8 tree edges, got {len(edges)}"
    return edges


def _make_mode1(
    cid: str,
    bp: List[Fraction],
    dens: List[List[Fraction]],
    m: Fraction,
    ell: List[Fraction],
    delta: Fraction,
) -> Dict[str, Any]:
    pcs = six_pieces_from_anchor(m, ell)
    vals_5x4 = [
        [eval_pw_const_valuation_q(bp, dens[i], pcs[f"P{j+1}"][0], pcs[f"P{j+1}"][1]) for j in range(4)]
        for i in range(5)
    ]
    adj = delta_favourite_graph(vals_5x4, delta)
    ok, matchings = check_hall_leaving_agent_robustness(adj)
    assert ok, f"Mode 1 {cid} not delta-robust!"
    gap_L = pcs["L"][1] - pcs["L"][0]
    gap_R = pcs["R"][1] - pcs["R"][0]
    empty_gap = "both" if (gap_L == 0 and gap_R == 0) else ("L" if gap_L == 0 else "R")
    return {
        "schema": SCHEMA_VERSION,
        "mode": "hall_robust_connectivity_lemma34_35_cert",
        "cert_id": cid,
        "valuations": _fmt_val(bp, dens),
        "anchor_m": format_rat(m),
        "ell_tuple": [format_rat(x) for x in ell],
        "delta": format_rat(delta),
        "claimed_empty_gap": empty_gap,
        "claimed_fav_graph_edge_count": sum(len(nb) for nb in adj),
        "claimed_is_delta_robust": True,
        "claimed_is_connected": True,
        "claimed_leaving_matchings": matchings,
    }


def _make_mode2(
    cid: str,
    weights: List[List[Fraction]],
    fav_mask: List[List[bool]],
) -> Dict[str, Any]:
    W = [sum((weights[i][j] for i in range(5)), Fraction(0, 1)) for j in range(4)]
    max_nf = max(
        (weights[i][j] for i in range(5) for j in range(4) if not fav_mask[i][j]),
        default=Fraction(0, 1),
    )
    adj = [[j for j in range(4) if fav_mask[i][j]] for i in range(5)]
    min_fav = [5, 5, 5, 5]
    for pmask in range(1, 16):
        P = [j for j in range(4) if (pmask >> j) & 1]
        k = len(P)
        for leave in range(5):
            cnt = sum(1 for a in range(5) if a != leave and any(j in adj[a] for j in P))
            if cnt < min_fav[k - 1]:
                min_fav[k - 1] = cnt
    return {
        "schema": SCHEMA_VERSION,
        "mode": "softmax_weight_balance_lemma39_cert",
        "cert_id": cid,
        "weights_5x4": [[format_rat(w) for w in row] for row in weights],
        "fav_mask_5x4": fav_mask,
        "claimed_piece_totals": [format_rat(x) for x in W],
        "claimed_max_nonfav_weight": format_rat(max_nf),
        "claimed_subset_min_fav_agents": min_fav,
        "claimed_hall_satisfied": True,
    }


def _make_mode3(
    cid: str,
    gamma: Fraction,
    bp: List[Fraction],
    dens: List[List[Fraction]],
    m: Fraction,
    ell_s: List[Fraction],
    ell_d: List[Fraction],
    delta: Fraction,
    mp: Fraction,
    ell_sp: List[Fraction],
) -> Dict[str, Any]:
    stab = max(abs(a - b) for a, b in zip(ell_d, ell_s))
    inv_g3 = Fraction(1, 1) / (gamma * gamma * gamma)
    l317 = Fraction(3, 1) * inv_g3 * delta
    shift_d = abs(m - mp)
    lip = max(abs(a - b) for a, b in zip(ell_s, ell_sp))
    l318 = Fraction(13, 1) * inv_g3 * shift_d
    return {
        "schema": SCHEMA_VERSION,
        "mode": "stability_and_lipschitz_lemma317_318_cert",
        "cert_id": cid,
        "gamma_hungry": format_rat(gamma),
        "valuations": _fmt_val(bp, dens),
        "anchor_m": format_rat(m),
        "ell_star_m": [format_rat(x) for x in ell_s],
        "ell_delta_m": [format_rat(x) for x in ell_d],
        "delta": format_rat(delta),
        "anchor_m_prime": format_rat(mp),
        "ell_star_m_prime": [format_rat(x) for x in ell_sp],
        "claimed_stability_linf": format_rat(stab),
        "claimed_lemma317_bound": format_rat(l317),
        "claimed_anchor_shift_d": format_rat(shift_d),
        "claimed_lipschitz_linf": format_rat(lip),
        "claimed_lemma318_bound": format_rat(l318),
    }


def _make_mode4(
    cid: str,
    bp: List[Fraction],
    dens: List[List[Fraction]],
    m: Fraction,
    ell: List[Fraction],
    eps: Fraction,
    fifth: str,
    alloc: List[str],
) -> Dict[str, Any]:
    pcs = six_pieces_from_anchor(m, ell)
    active = ["P1", "P2", "P3", "P4", fifth]
    val_map = [
        {nm: eval_pw_const_valuation_q(bp, dens[i], pcs[nm][0], pcs[nm][1]) for nm in active}
        for i in range(5)
    ]
    max_envy = max(
        val_map[i][nm] - val_map[i][alloc[i]]
        for i in range(5)
        for nm in active
    )
    if max_envy < Fraction(0, 1):
        max_envy = Fraction(0, 1)
    vals_5x4 = [[val_map[i][f"P{j+1}"] for j in range(4)] for i in range(5)]
    adj_eps = delta_favourite_graph(vals_5x4, eps)
    tree = _find_spanning_tree(adj_eps)
    return {
        "schema": SCHEMA_VERSION,
        "mode": "complete_ef5_allocation_theorem1_2_cert",
        "cert_id": cid,
        "valuations": _fmt_val(bp, dens),
        "anchor_m": format_rat(m),
        "ell_tuple": [format_rat(x) for x in ell],
        "target_eps": format_rat(eps),
        "fifth_piece_name": fifth,
        "allocation_5": alloc,
        "spanning_tree_edges": tree,
        "claimed_max_envy": format_rat(max_envy),
        "claimed_total_length": "1",
        "claimed_tree_valid": True,
        "claimed_eps_ef_verified": True,
    }


def main() -> None:
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Shared valuation families (all strictly monotone 1-Lipschitz piecewise-constant densities in [0, 1])
    # V_unif: uniform densities d = 1 everywhere (1-strongly hungry!)
    bp_u = [Fraction(0, 1), Fraction(1, 1)]
    d_unif = [[Fraction(1, 1)] for _ in range(5)]

    # V_het5: 5 breakpoints [0, 1/5, 2/5, 3/5, 4/5, 1], heterogeneous strong-hungry densities in [1/2, 1]!
    bp_5 = [Fraction(k, 5) for k in range(6)]
    # Design V_het5 so each agent i prefers segment i (density 1) and values others at 1/2:
    # At m = 2/5, ell = [1/5, 1/5, 1/5, 1/5] (L empty, R = [3/5, 4/5]):
    #   P1=[0,1/5], P2=[1/5,2/5], P3=[2/5,3/5], R=[3/5,4/5], P4=[4/5,1].
    # Wait: for robustness on P1..P4 when agent 3 (who prefers R) is present, we need 5 agents to cover P1..P4 robustly!
    # So give all 5 agents densities tailored so each P1..P4 has >= 2 agents favouring it!
    # Specifically, for uniform-like perturbed heterogeneous densities on [0, 1/4, 1/2, 3/4, 1]:
    bp_4 = [Fraction(k, 4) for k in range(5)]
    # Agent 0 favors P1 & P2 (1, 1, 1/2, 1/2)
    # Agent 1 favors P2 & P3 (1/2, 1, 1, 1/2)
    # Agent 2 favors P3 & P4 (1/2, 1/2, 1, 1)
    # Agent 3 favors P4 & P1 (1, 1/2, 1/2, 1)
    # Agent 4 favors all four equally (3/4, 3/4, 3/4, 3/4) -> degree-4 hub connecting the cycle!
    d_cycle4 = [
        [Fraction(1, 1), Fraction(1, 1), Fraction(1, 2), Fraction(1, 2)],
        [Fraction(1, 2), Fraction(1, 1), Fraction(1, 1), Fraction(1, 2)],
        [Fraction(1, 2), Fraction(1, 2), Fraction(1, 1), Fraction(1, 1)],
        [Fraction(1, 1), Fraction(1, 2), Fraction(1, 2), Fraction(1, 1)],
        [Fraction(3, 4), Fraction(3, 4), Fraction(3, 4), Fraction(3, 4)],
    ]

    # V_asym5: 5-segment asymmetric heterogeneous valuations on [0, 1/5, 2/5, 3/5, 4/5, 1]
    # Pieces at m = 2/5, ell = [1/5, 1/5, 1/5, 1/5]: P1=[0,1/5], P2=[1/5,2/5], P3=[2/5,3/5], R=[3/5,4/5], P4=[4/5,1]
    # Make R=[3/5,4/5] a joint favourite of Agent 4 (and <= favourite for Agents 0..3),
    # while P1..P4 form a 0-robust cycle across Agents 0..4!
    d_asym5 = [
        [Fraction(1, 1), Fraction(1, 1), Fraction(1, 2), Fraction(3, 4), Fraction(1, 2)],
        [Fraction(1, 2), Fraction(1, 1), Fraction(1, 1), Fraction(3, 4), Fraction(1, 2)],
        [Fraction(1, 2), Fraction(1, 2), Fraction(1, 1), Fraction(3, 4), Fraction(1, 1)],
        [Fraction(1, 1), Fraction(1, 2), Fraction(1, 2), Fraction(3, 4), Fraction(1, 1)],
        [Fraction(4, 5), Fraction(4, 5), Fraction(4, 5), Fraction(4, 5), Fraction(4, 5)],
    ]

    # V_left_gap: L = [1/5, 2/5] is the non-empty fifth piece (R empty: m = 3/5, ell = [1/5, 1/5, 1/5, 1/5])
    # Pieces: P1=[0,1/5], L=[1/5,2/5], P2=[2/5,3/5], P3=[3/5,4/5], P4=[4/5,1]
    d_left5 = [
        [Fraction(1, 1), Fraction(3, 5), Fraction(1, 1), Fraction(1, 2), Fraction(1, 2)],
        [Fraction(1, 2), Fraction(3, 5), Fraction(1, 1), Fraction(1, 1), Fraction(1, 2)],
        [Fraction(1, 2), Fraction(3, 5), Fraction(1, 2), Fraction(1, 1), Fraction(1, 1)],
        [Fraction(1, 1), Fraction(3, 5), Fraction(1, 2), Fraction(1, 2), Fraction(1, 1)],
        [Fraction(3, 4), Fraction(3, 4), Fraction(3, 4), Fraction(3, 4), Fraction(3, 4)],
    ]

    certs: List[Dict[str, Any]] = []

    # --- Mode 1: 4 Lemma 3.4-3.5 Leaving-Agent Hall Robustness & Connectivity Certificates ---
    # 1.1: Exact 0-robust complete cycle + hub on [0, 1/4, 1/2, 3/4, 1] (m=1/2, both gaps empty)
    certs.append(_make_mode1(
        "m1_hall_exact_0rob_cycle_hub", bp_4, d_cycle4,
        Fraction(1, 2), [Fraction(1, 4)] * 4, Fraction(0, 1),
    ))
    # 1.2: Exact 0-robust with non-empty R gap (m=2/5, L empty) on asymmetric 5-segment valuations
    certs.append(_make_mode1(
        "m1_hall_exact_0rob_right_gap", bp_5, d_asym5,
        Fraction(2, 5), [Fraction(1, 5)] * 4, Fraction(0, 1),
    ))
    # 1.3: Exact 0-robust with non-empty L gap (m=3/5, R empty)
    certs.append(_make_mode1(
        "m1_hall_exact_0rob_left_gap", bp_5, d_left5,
        Fraction(3, 5), [Fraction(1, 5)] * 4, Fraction(0, 1),
    ))
    # 1.4: Perturbed delta-robust maximal tuple (m=2/5, ell=[11/50, 9/50, 1/5, 1/5], delta=1/25)
    certs.append(_make_mode1(
        "m1_hall_delta_rob_perturbed", bp_5, d_asym5,
        Fraction(2, 5), [Fraction(11, 50), Fraction(9, 50), Fraction(1, 5), Fraction(1, 5)], Fraction(1, 25),
    ))

    # --- Mode 2: 4 Lemma 3.7 & 3.9 Softmax Weight Balance Certificates (W_j = 5/4, non-fav <= 1/32) ---
    # 2.1: Exact uniform 1/4 softmax weights (all 20 edges favourite, max non-fav = 0)
    certs.append(_make_mode2(
        "m2_softmax_uniform_exact",
        [[Fraction(1, 4)] * 4 for _ in range(5)],
        [[True] * 4 for _ in range(5)],
    ))
    # 2.2: Sparse cycle+hub with exact non-fav cap 1/32 (sharp Lemma 3.9 boundary!)
    # Agents 0..3 have 2 favs (each 15/32) and 2 non-favs (each 1/32); sum per agent = 32/32 = 1.
    # Each piece gets 2*(15/32) + 2*(1/32) = 32/32 = 1 from agents 0..3, plus 1/4 from agent 4 -> W_j = 5/4!
    w22 = [
        [Fraction(15, 32), Fraction(15, 32), Fraction(1, 32), Fraction(1, 32)],
        [Fraction(1, 32), Fraction(15, 32), Fraction(15, 32), Fraction(1, 32)],
        [Fraction(1, 32), Fraction(1, 32), Fraction(15, 32), Fraction(15, 32)],
        [Fraction(15, 32), Fraction(1, 32), Fraction(1, 32), Fraction(15, 32)],
        [Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)],
    ]
    f22 = [
        [True, True, False, False],
        [False, True, True, False],
        [False, False, True, True],
        [True, False, False, True],
        [True, True, True, True],
    ]
    certs.append(_make_mode2("m2_softmax_sharp_cap_1_32", w22, f22))

    # 2.3: Asymmetric 1-fav + 2-fav + 3-fav mixed softmax balance with non-fav = 1/64
    # Agent 0: [61/64, 1/64, 1/64, 1/64] (only P1 fav!)
    # Agent 1: [1/64, 61/64, 1/64, 1/64] (only P2 fav!)
    # Agent 2: [1/64, 1/64, 61/64, 1/64] (only P3 fav!)
    # Agent 3: [1/64, 1/64, 1/64, 61/64] (only P4 fav!)
    # Agent 4: [1/4, 1/4, 1/4, 1/4] (all 4 fav -> W_j = 61/64 + 3/64 + 16/64 = 80/64 = 5/4! And 8-edge star+4!)
    w23 = [
        [Fraction(61, 64), Fraction(1, 64), Fraction(1, 64), Fraction(1, 64)],
        [Fraction(1, 64), Fraction(61, 64), Fraction(1, 64), Fraction(1, 64)],
        [Fraction(1, 64), Fraction(1, 64), Fraction(61, 64), Fraction(1, 64)],
        [Fraction(1, 64), Fraction(1, 64), Fraction(1, 64), Fraction(61, 64)],
        [Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)],
    ]
    f23 = [
        [True, False, False, False],
        [False, True, False, False],
        [False, False, True, False],
        [False, False, False, True],
        [True, True, True, True],
    ]
    certs.append(_make_mode2("m2_softmax_minimal_8edge_tree", w23, f23))

    # 2.4: Non-symmetric irregular rational softmax balance (non-uniform agent degrees: 3, 2, 2, 2, 3)
    # Row 0: [1/2, 3/8, 1/8, 0]   (3 favs)
    # Row 1: [0, 5/8, 3/8, 0]     (2 favs)
    # Row 2: [0, 0, 1/2, 1/2]     (2 favs)
    # Row 3: [1/2, 0, 0, 1/2]     (2 favs)
    # Row 4: [1/4, 1/4, 1/4, 1/4] (4 favs) -> sums: [5/4, 5/4, 5/4, 5/4]!!
    w24 = [
        [Fraction(1, 2), Fraction(3, 8), Fraction(1, 8), Fraction(0, 1)],
        [Fraction(0, 1), Fraction(5, 8), Fraction(3, 8), Fraction(0, 1)],
        [Fraction(0, 1), Fraction(0, 1), Fraction(1, 2), Fraction(1, 2)],
        [Fraction(1, 2), Fraction(0, 1), Fraction(0, 1), Fraction(1, 2)],
        [Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)],
    ]
    f24 = [
        [True, True, True, False],
        [False, True, True, False],
        [False, False, True, True],
        [True, False, False, True],
        [True, True, True, True],
    ]
    certs.append(_make_mode2("m2_softmax_asymmetric_degrees", w24, f24))

    # --- Mode 3: 4 Lemma 3.17 & 3.18 Quantitative Stability & Lipschitz Continuity Certificates ---
    # 3.1: Uniform gamma=1 valuations: at m=2/5, ell*=[1/5,1/5,1/5,1/5]; perturbed ell_d=[21/100,19/100,1/5,1/5] (delta=1/50);
    #      at m'=11/25, ell*(m')=[11/50, 11/50, 11/50, 11/50] (L empty, R=3/25)!
    certs.append(_make_mode3(
        "m3_stab_lip_uniform_g1", Fraction(1, 1), bp_u, d_unif,
        Fraction(2, 5), [Fraction(1, 5)] * 4,
        [Fraction(21, 100), Fraction(19, 100), Fraction(1, 5), Fraction(1, 5)], Fraction(1, 50),
        Fraction(11, 25), [Fraction(11, 50)] * 4,
    ))
    # 3.2: Uniform gamma=1 across larger anchor shift m=3/10 -> m'=7/20
    certs.append(_make_mode3(
        "m3_stab_lip_uniform_shift_1_20", Fraction(1, 1), bp_u, d_unif,
        Fraction(3, 10), [Fraction(3, 20)] * 4,
        [Fraction(16, 100), Fraction(14, 100), Fraction(3, 20), Fraction(3, 20)], Fraction(1, 50),
        Fraction(7, 20), [Fraction(7, 40)] * 4,
    ))
    # 3.3: Heterogeneous gamma=1/2 (d_asym5) at m=2/5 vs m'=19/50
    # Check 0-robust at m'=19/50 on d_asym5: ell*(19/50) = [19/100, 19/100, 19/100, 19/100]:
    # Since all 4 pieces lie inside their respective 1/5 segments ([0,1/5], [1/5,2/5], [2/5,3/5], [4/5,1]):
    # Wait: P2 = [19/100, 38/100] straddles 1/5 = 20/100! Instead use 2-region symmetric [0, 1/2, 1] with gamma=1/2!
    bp_2 = [Fraction(0, 1), Fraction(1, 2), Fraction(1, 1)]
    d_half = [[Fraction(1, 2), Fraction(1, 2)] for _ in range(5)]
    certs.append(_make_mode3(
        "m3_stab_lip_gamma_1_2", Fraction(1, 2), bp_2, d_half,
        Fraction(2, 5), [Fraction(1, 5)] * 4,
        [Fraction(21, 100), Fraction(19, 100), Fraction(1, 5), Fraction(1, 5)], Fraction(1, 100),
        Fraction(9, 20), [Fraction(9, 40)] * 4,
    ))
    # 3.4: Heterogeneous gamma=3/4 valuations on [0, 1] (uniform 3/4 density, m=3/5 -> m'=11/20, right-tight!)
    d_34 = [[Fraction(3, 4)] for _ in range(5)]
    certs.append(_make_mode3(
        "m3_stab_lip_right_tight_g3_4", Fraction(3, 4), bp_u, d_34,
        Fraction(3, 5), [Fraction(1, 5)] * 4,
        [Fraction(1, 5), Fraction(1, 5), Fraction(21, 100), Fraction(19, 100)], Fraction(3, 200),
        Fraction(11, 20), [Fraction(9, 40)] * 4,
    ))

    # --- Mode 4: 4 Theorems 1 & 2 Complete 5-Agent Contiguous EF / eps-EF Certificates ---
    # 4.1: Exact 0-EF complete allocation on heterogeneous asymmetric 5-segment valuations (R = [3/5, 4/5])
    certs.append(_make_mode4(
        "m4_ef5_exact_0envy_right_gap", bp_5, d_asym5,
        Fraction(2, 5), [Fraction(1, 5)] * 4, Fraction(0, 1),
        "R", ["P1", "P2", "P3", "P4", "R"],
    ))
    # 4.2: Exact 0-EF complete allocation on left-gap heterogeneous valuations (L = [1/5, 2/5])
    certs.append(_make_mode4(
        "m4_ef5_exact_0envy_left_gap", bp_5, d_left5,
        Fraction(3, 5), [Fraction(1, 5)] * 4, Fraction(0, 1),
        "L", ["P1", "P2", "P3", "P4", "L"],
    ))
    # 4.3: Exact 0-EF on uniform valuations (m=2/5, all 5 pieces exact length 1/5)
    certs.append(_make_mode4(
        "m4_ef5_exact_0envy_uniform", bp_u, d_unif,
        Fraction(2, 5), [Fraction(1, 5)] * 4, Fraction(0, 1),
        "R", ["P1", "P2", "P3", "P4", "R"],
    ))
    # 4.4: Approximate eps-EF allocation (Theorem 2 bisection output: m=41/100, ell=[21/100, 1/5, 1/5, 19/100], eps=1/25)
    certs.append(_make_mode4(
        "m4_ef5_approx_eps_1_25_bisect", bp_5, d_asym5,
        Fraction(41, 100), [Fraction(21, 100), Fraction(1, 5), Fraction(1, 5), Fraction(19, 100)], Fraction(1, 25),
        "R", ["P1", "P2", "P3", "P4", "R"],
    ))

    replay_rows: List[Dict[str, Any]] = []
    for cert in certs:
        out_path = CERT_DIR / f"{cert['cert_id']}.json"
        out_path.write_text(json.dumps(cert, indent=2) + "\n", encoding="utf-8")
        t0 = time.perf_counter()
        summary = verify_cake5_certificate_exact(cert)
        ms = round((time.perf_counter() - t0) * 1000.0, 3)
        replay_rows.append({"cert_id": cert["cert_id"], "mode": cert["mode"], "verify_ms": ms, "summary": summary})

    (DATA_DIR / "certificate_replay_summary.json").write_text(
        json.dumps({"count": len(replay_rows), "certificates": replay_rows}, indent=2) + "\n",
        encoding="utf-8",
    )

    # Experiment 1: Lemma 3.9 Hall-margin ceiling across all 4 subset sizes |P| = 1..4
    exp1_rows = []
    for k in range(1, 5):
        raw_lb = Fraction(5 * k, 4) - Fraction(1, 1) - Fraction(4 * k, 32)  # = (9k - 8)/8
        exp1_rows.append({
            "subset_size_k": k,
            "raw_weight_lb_rat": format_rat(raw_lb),
            "raw_weight_lb_float": round(raw_lb.numerator / raw_lb.denominator, 6),
            "hall_required_k": k,
            "margin_above_k_minus_1": round((raw_lb - Fraction(k - 1, 1)).numerator / (raw_lb - Fraction(k - 1, 1)).denominator, 6),
        })
    (DATA_DIR / "exp1_lemma39_hall_margin.json").write_text(
        json.dumps({"rows": exp1_rows}, indent=2) + "\n", encoding="utf-8"
    )

    # Experiment 2: Query complexity scaling O(log^3(1/eps)) vs O(log^5(1/eps)) vs brute-force (1/eps)^4
    exp2_rows = []
    for p in range(2, 11):
        # L = log2(1/eps) = p -> 1/eps = 2^p
        exp2_rows.append({
            "log2_inv_eps": p,
            "tree_enum_L3": p ** 3,
            "nested_5_L5": p ** 5,
            "grid_brute_2p": 1 << p,
        })
    (DATA_DIR / "exp2_query_complexity_scaling.json").write_text(
        json.dumps({"rows": exp2_rows}, indent=2) + "\n", encoding="utf-8"
    )

    # Experiment 3: Mode 3 stability & Lipschitz actual vs theoretical bounds
    exp3_rows = []
    for r in replay_rows:
        if r["mode"] == "stability_and_lipschitz_lemma317_318_cert":
            c = json.loads((CERT_DIR / f"{r['cert_id']}.json").read_text(encoding="utf-8"))
            s_act = Fraction(c["claimed_stability_linf"])
            s_ub = Fraction(c["claimed_lemma317_bound"])
            l_act = Fraction(c["claimed_lipschitz_linf"])
            l_ub = Fraction(c["claimed_lemma318_bound"])
            exp3_rows.append({
                "cert_id": r["cert_id"],
                "gamma": c["gamma_hungry"],
                "stab_ratio": round((s_act / s_ub).numerator / (s_act / s_ub).denominator, 6),
                "lip_ratio": round((l_act / l_ub).numerator / (l_act / l_ub).denominator, 6),
            })
    (DATA_DIR / "exp3_stability_lipschitz_headroom.json").write_text(
        json.dumps({"rows": exp3_rows}, indent=2) + "\n", encoding="utf-8"
    )

    # Experiment 4: Mode 4 complete 5-agent EF/eps-EF audit summary
    exp4_rows = [
        r["summary"] | {"cert_id": r["cert_id"], "verify_ms": r["verify_ms"]}
        for r in replay_rows
        if r["mode"] == "complete_ef5_allocation_theorem1_2_cert"
    ]
    (DATA_DIR / "exp4_complete_ef5_audit.json").write_text(
        json.dumps({"rows": exp4_rows}, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Generated {len(replay_rows)} canonical {SCHEMA_VERSION} certificates and 4 experiment JSONs.")
    for r in replay_rows:
        print(f"  {r['cert_id']:40s} {r['verify_ms']:6.3f} ms  ({r['mode']})")


if __name__ == "__main__":
    main()
