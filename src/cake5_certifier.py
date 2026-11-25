"""Zero-floating-point exact-Q certificate verifier: EF-CAKE5-CERT-1.0.
Audits all four graph-theoretic, softmax-weight, stability/Lipschitz, and complete-allocation
pillars of Aris Filos-Ratsikas, Alexandros Hollender, Mohamad Latifian, & Giannis Tyrovolas
(arXiv:2611.33149, Nov 24, 2026) "Envy-Free Cake-Cutting for Five Agents":
  - Mode 1: hall_robust_connectivity_lemma34_35_cert (Defs. 3.1-3.3 & Lemmas 3.4-3.5)
  - Mode 2: softmax_weight_balance_lemma39_cert (Lemmas 3.7 & 3.9 W_j = 5/4 => Hall robustness)
  - Mode 3: stability_and_lipschitz_lemma317_318_cert (Lemmas 3.17 & 3.18 quantitative bounds)
  - Mode 4: complete_ef5_allocation_theorem1_2_cert (Theorems 1 & 2 complete 5-agent EF/eps-EF)

Author: Lluis Eriksson
License: MIT
"""
from __future__ import annotations

import re
from fractions import Fraction
from typing import Any, Dict, List, Set, Tuple

from src.cake5_exact import (
    check_hall_leaving_agent_robustness,
    check_spanning_tree_5x4,
    delta_favourite_graph,
    eval_pw_const_valuation_q,
    format_rat,
    is_bipartite_connected_5x4,
    six_pieces_from_anchor,
)

SCHEMA_VERSION = "EF-CAKE5-CERT-1.0"
_CANON_INT_RE = re.compile(r"\A(0|-?[1-9][0-9]*)\Z")
_CANON_FRAC_RE = re.compile(r"\A-?[1-9][0-9]*/[1-9][0-9]*\Z")
MAX_RAT_STR_LEN = 1024
MAX_INT_BITS = 2048
MAX_ID_LEN = 128
MAX_JSON_DEPTH = 32


class Cake5CertificateError(ValueError):
    """Raised whenever an EF-CAKE5-CERT-1.0 certificate fails any invariant."""


def _assert_strict_json_types(obj: Any, path: str = "$", depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise Cake5CertificateError(f"JSON nesting depth > {MAX_JSON_DEPTH} at {path}")
    t = type(obj)
    if t is int:
        if obj.bit_length() > MAX_INT_BITS:
            raise Cake5CertificateError(f"Integer bit-length > {MAX_INT_BITS} at {path}")
        return
    if t is str or t is bool:
        return
    if t is list:
        for i, v in enumerate(obj):
            _assert_strict_json_types(v, f"{path}[{i}]", depth + 1)
        return
    if t is dict:
        for k, v in obj.items():
            if type(k) is not str:
                raise Cake5CertificateError(f"Non-string dict key at {path}")
            _assert_strict_json_types(v, f"{path}.{k}", depth + 1)
        return
    raise Cake5CertificateError(f"Forbidden JSON type {t.__name__} at {path}")


def _parse_int(val: Any, name: str) -> int:
    if type(val) is not int:
        raise Cake5CertificateError(f"{name} must be strict int, got {type(val).__name__}")
    if val.bit_length() > MAX_INT_BITS:
        raise Cake5CertificateError(f"{name} integer too large")
    return val


def _parse_rat(val: Any, name: str) -> Fraction:
    if type(val) is int:
        if val.bit_length() > MAX_INT_BITS:
            raise Cake5CertificateError(f"{name} integer too large")
        return Fraction(val, 1)
    if type(val) is str:
        if len(val) > MAX_RAT_STR_LEN:
            raise Cake5CertificateError(f"{name} rational string too long")
        if _CANON_INT_RE.match(val):
            iv = int(val)
            if iv.bit_length() > MAX_INT_BITS:
                raise Cake5CertificateError(f"{name} integer bit-length > {MAX_INT_BITS}")
            return Fraction(iv, 1)
        if _CANON_FRAC_RE.match(val):
            num_s, den_s = val.split("/")
            num, den = int(num_s), int(den_s)
            if num.bit_length() > MAX_INT_BITS or den.bit_length() > MAX_INT_BITS:
                raise Cake5CertificateError(f"{name} rational bit-length > {MAX_INT_BITS}")
            if den < 2:
                raise Cake5CertificateError(f"{name} denominator must be >= 2: {val!r}")
            q = Fraction(num, den)
            if q.numerator != num or q.denominator != den:
                raise Cake5CertificateError(f"{name} unreduced fraction: {val!r}")
            return q
        raise Cake5CertificateError(f"{name} non-canonical rational string: {val!r}")
    raise Cake5CertificateError(f"{name} invalid type {type(val).__name__}")


def _parse_exact_keys(cert: Dict[str, Any], req: Set[str], mode: str) -> None:
    keys = set(cert.keys())
    if keys != req:
        raise Cake5CertificateError(f"{mode} key mismatch: {sorted(keys ^ req)}")


def _parse_valuations_5(
    raw: Any,
    require_gamma_hungry: Fraction | None = None,
) -> Tuple[List[Fraction], List[List[Fraction]]]:
    """Parse 5 piecewise-constant monotone 1-Lipschitz valuations sharing breakpoints 0=b_0<...<b_K=1."""
    if type(raw) is not dict:
        raise Cake5CertificateError("valuations must be dict")
    _parse_exact_keys(raw, {"breakpoints", "densities_5"}, "valuations")
    raw_bp = raw["breakpoints"]
    if type(raw_bp) is not list or not (2 <= len(raw_bp) <= 32):
        raise Cake5CertificateError("breakpoints must have length in [2, 32]")
    bp = [_parse_rat(v, f"breakpoints[{i}]") for i, v in enumerate(raw_bp)]
    if bp[0] != Fraction(0, 1) or bp[-1] != Fraction(1, 1):
        raise Cake5CertificateError("breakpoints must start at 0 and end at 1")
    for i in range(len(bp) - 1):
        if bp[i] >= bp[i + 1]:
            raise Cake5CertificateError("breakpoints must be strictly increasing")
    K = len(bp) - 1

    raw_d = raw["densities_5"]
    if type(raw_d) is not list or len(raw_d) != 5:
        raise Cake5CertificateError("densities_5 must have 5 rows")
    dens: List[List[Fraction]] = []
    for a in range(5):
        if type(raw_d[a]) is not list or len(raw_d[a]) != K:
            raise Cake5CertificateError(f"densities_5[{a}] must have length {K}")
        row = [_parse_rat(raw_d[a][k], f"dens[{a}][{k}]") for k in range(K)]
        for k, dv in enumerate(row):
            if dv < Fraction(0, 1) or dv > Fraction(1, 1):
                raise Cake5CertificateError(f"Density {dv} violates monotone 1-Lipschitz [0, 1] bound")
            if require_gamma_hungry is not None and dv < require_gamma_hungry:
                raise Cake5CertificateError(f"Density {dv} violates gamma={require_gamma_hungry}-strong hungriness")
        dens.append(row)
    return bp, dens


def _parse_maximal_feasible_tuple(m: Fraction, raw_ell: Any, name: str) -> List[Fraction]:
    if not (Fraction(0, 1) <= m <= Fraction(1, 1)):
        raise Cake5CertificateError("Anchor m must lie in [0, 1]")
    if type(raw_ell) is not list or len(raw_ell) != 4:
        raise Cake5CertificateError(f"{name} must be 4-tuple [l1, l2, l3, l4]")
    ell = [_parse_rat(raw_ell[j], f"{name}[{j}]") for j in range(4)]
    if any(x < Fraction(0, 1) for x in ell):
        raise Cake5CertificateError(f"{name} contains negative length")
    if ell[0] + ell[1] > m or ell[2] + ell[3] > Fraction(1, 1) - m:
        raise Cake5CertificateError(f"{name} violates feasibility (l1+l2 <= m and l3+l4 <= 1-m)")
    if ell[0] + ell[1] != m and ell[2] + ell[3] != Fraction(1, 1) - m:
        raise Cake5CertificateError(f"{name} is NOT maximal (neither l1+l2=m nor l3+l4=1-m)")
    return ell


# =============================================================================
# Mode 1: Defs. 3.1-3.3 & Lemmas 3.4-3.5 Leaving-Agent Hall Robustness & Connectivity
# =============================================================================


def _verify_mode1_hall_robust(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema",
        "mode",
        "cert_id",
        "valuations",
        "anchor_m",
        "ell_tuple",
        "delta",
        "claimed_empty_gap",
        "claimed_fav_graph_edge_count",
        "claimed_is_delta_robust",
        "claimed_is_connected",
        "claimed_leaving_matchings",
    }
    _parse_exact_keys(cert, req, "Mode 1")
    bp, dens = _parse_valuations_5(cert["valuations"])
    m = _parse_rat(cert["anchor_m"], "anchor_m")
    ell = _parse_maximal_feasible_tuple(m, cert["ell_tuple"], "ell_tuple")
    delta = _parse_rat(cert["delta"], "delta")
    if delta < Fraction(0, 1):
        raise Cake5CertificateError("delta must be >= 0")

    pcs = six_pieces_from_anchor(m, ell)
    vals_5x4 = [
        [eval_pw_const_valuation_q(bp, dens[i], pcs[f"P{j+1}"][0], pcs[f"P{j+1}"][1]) for j in range(4)]
        for i in range(5)
    ]
    adj = delta_favourite_graph(vals_5x4, delta)
    edge_cnt = sum(len(nb) for nb in adj)
    is_rob, _ = check_hall_leaving_agent_robustness(adj)
    if not is_rob:
        raise Cake5CertificateError("Tuple ell is NOT delta-robust (Lemma 3.4 Hall condition failed)")
    is_conn = is_bipartite_connected_5x4(adj)
    if not is_conn:
        raise Cake5CertificateError("Lemma 3.5 connectivity failed")

    # Verify witness leaving-agent matchings explicitly!
    raw_m = cert["claimed_leaving_matchings"]
    if type(raw_m) is not list or len(raw_m) != 5:
        raise Cake5CertificateError("claimed_leaving_matchings must have 5 entries (one per departing agent)")
    for leave in range(5):
        rem = [a for a in range(5) if a != leave]
        row = raw_m[leave]
        if type(row) is not list or len(row) != 4:
            raise Cake5CertificateError(f"leaving_matchings[{leave}] must assign 4 pieces")
        assigned = [_parse_int(v, f"matching[{leave}]") for v in row]
        if sorted(assigned) != [0, 1, 2, 3]:
            raise Cake5CertificateError(f"leaving_matchings[{leave}] is not a permutation of 0..3")
        for a, pj in zip(rem, assigned):
            if pj not in adj[a]:
                raise Cake5CertificateError(
                    f"leaving_matchings[{leave}] assigns non-delta-favourite piece P{pj+1} to agent {a}"
                )

    gap_L = pcs["L"][1] - pcs["L"][0]
    gap_R = pcs["R"][1] - pcs["R"][0]
    if gap_L == 0 and gap_R == 0:
        empty_gap = "both"
    elif gap_L == 0:
        empty_gap = "L"
    else:
        empty_gap = "R"

    if cert["claimed_empty_gap"] != empty_gap:
        raise Cake5CertificateError(f"claimed_empty_gap {cert['claimed_empty_gap']!r} != {empty_gap!r}")
    if _parse_int(cert["claimed_fav_graph_edge_count"], "claimed_fav_graph_edge_count") != edge_cnt:
        raise Cake5CertificateError("claimed_fav_graph_edge_count mismatch")
    if cert["claimed_is_delta_robust"] is not True or cert["claimed_is_connected"] is not True:
        raise Cake5CertificateError("claimed_is_delta_robust and claimed_is_connected must be true")

    return {
        "verified": True,
        "mode": cert["mode"],
        "edge_count": edge_cnt,
        "empty_gap": empty_gap,
        "delta": format_rat(delta),
    }


# =============================================================================
# Mode 2: Lemmas 3.7 & 3.9 Softmax Weight Balance W_j = 5/4 => Hall Robustness
# =============================================================================


def _verify_mode2_softmax_balance(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema",
        "mode",
        "cert_id",
        "weights_5x4",
        "fav_mask_5x4",
        "claimed_piece_totals",
        "claimed_max_nonfav_weight",
        "claimed_subset_min_fav_agents",
        "claimed_hall_satisfied",
    }
    _parse_exact_keys(cert, req, "Mode 2")
    raw_w = cert["weights_5x4"]
    raw_f = cert["fav_mask_5x4"]
    if type(raw_w) is not list or len(raw_w) != 5 or type(raw_f) is not list or len(raw_f) != 5:
        raise Cake5CertificateError("weights_5x4 and fav_mask_5x4 must be 5x4")

    W = [Fraction(0, 1)] * 4
    max_nonfav = Fraction(0, 1)
    adj: List[List[int]] = []
    weights: List[List[Fraction]] = []
    for i in range(5):
        if type(raw_w[i]) is not list or len(raw_w[i]) != 4 or type(raw_f[i]) is not list or len(raw_f[i]) != 4:
            raise Cake5CertificateError(f"Row {i} must have length 4")
        if not all(type(b) is bool for b in raw_f[i]):
            raise Cake5CertificateError(f"fav_mask_5x4[{i}] must contain strict booleans")
        wrow = [_parse_rat(raw_w[i][j], f"w[{i}][{j}]") for j in range(4)]
        if any(w < 0 for w in wrow) or sum(wrow, Fraction(0, 1)) != Fraction(1, 1):
            raise Cake5CertificateError(f"Agent {i} weights must be non-negative and sum to 1 (Lemma 3.7)")
        weights.append(wrow)
        frow: List[int] = []
        for j in range(4):
            W[j] += wrow[j]
            if raw_f[i][j]:
                frow.append(j)
            else:
                if wrow[j] > Fraction(1, 32):
                    raise Cake5CertificateError(
                        f"Non-favourite weight w[{i}][{j}]={wrow[j]} exceeds Lemma 3.9 cap 2^(-5)=1/32"
                    )
                if wrow[j] > max_nonfav:
                    max_nonfav = wrow[j]
        if not frow:
            raise Cake5CertificateError(f"Agent {i} has no favourite piece")
        adj.append(frow)

    # Lemma 3.9 hypothesis: W_j == 5/4 for every piece j in 0..3
    for j in range(4):
        if W[j] != Fraction(5, 4):
            raise Cake5CertificateError(f"Piece weight W_{j+1}={W[j]} != 5/4")

    # Exhaustively verify Lemma 3.9 Hall margin for all 15 non-empty piece subsets P subset [4]
    # and all 5 departing agents i
    min_fav_by_size = [5, 5, 5, 5]
    for pmask in range(1, 16):
        P = [j for j in range(4) if (pmask >> j) & 1]
        k = len(P)
        for leave in range(5):
            fav_agents = [a for a in range(5) if a != leave and any(j in adj[a] for j in P)]
            if len(fav_agents) < k:
                raise Cake5CertificateError(f"Hall condition violated for subset P={P} without agent {leave}")
            if len(fav_agents) < min_fav_by_size[k - 1]:
                min_fav_by_size[k - 1] = len(fav_agents)

    is_rob, _ = check_hall_leaving_agent_robustness(adj)
    if not is_rob:
        raise Cake5CertificateError("Induced favourite graph failed Lemma 3.4 robustness")

    raw_pt = cert["claimed_piece_totals"]
    if type(raw_pt) is not list or len(raw_pt) != 4 or [_parse_rat(v, "W_j") for v in raw_pt] != W:
        raise Cake5CertificateError("claimed_piece_totals mismatch")
    if _parse_rat(cert["claimed_max_nonfav_weight"], "claimed_max_nonfav_weight") != max_nonfav:
        raise Cake5CertificateError("claimed_max_nonfav_weight mismatch")
    raw_mf = cert["claimed_subset_min_fav_agents"]
    if type(raw_mf) is not list or len(raw_mf) != 4 or [_parse_int(v, "min_fav") for v in raw_mf] != min_fav_by_size:
        raise Cake5CertificateError("claimed_subset_min_fav_agents mismatch")
    if cert["claimed_hall_satisfied"] is not True:
        raise Cake5CertificateError("claimed_hall_satisfied must be true")

    return {
        "verified": True,
        "mode": cert["mode"],
        "max_nonfav": format_rat(max_nonfav),
        "min_fav_by_size": min_fav_by_size,
    }


# =============================================================================
# Mode 3: Lemmas 3.17 & 3.18 Quantitative Stability & Lipschitz Continuity Audit
# =============================================================================


def _verify_mode3_stability_lipschitz(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema",
        "mode",
        "cert_id",
        "gamma_hungry",
        "valuations",
        "anchor_m",
        "ell_star_m",
        "ell_delta_m",
        "delta",
        "anchor_m_prime",
        "ell_star_m_prime",
        "claimed_stability_linf",
        "claimed_lemma317_bound",
        "claimed_anchor_shift_d",
        "claimed_lipschitz_linf",
        "claimed_lemma318_bound",
    }
    _parse_exact_keys(cert, req, "Mode 3")
    gamma = _parse_rat(cert["gamma_hungry"], "gamma_hungry")
    if not (Fraction(0, 1) < gamma <= Fraction(1, 1)):
        raise Cake5CertificateError("Require 0 < gamma_hungry <= 1")
    bp, dens = _parse_valuations_5(cert["valuations"], require_gamma_hungry=gamma)

    m = _parse_rat(cert["anchor_m"], "anchor_m")
    mp = _parse_rat(cert["anchor_m_prime"], "anchor_m_prime")
    delta = _parse_rat(cert["delta"], "delta")
    if delta <= Fraction(0, 1) or m == mp:
        raise Cake5CertificateError("Require delta > 0 and anchor_m != anchor_m_prime")

    ell_s = _parse_maximal_feasible_tuple(m, cert["ell_star_m"], "ell_star_m")
    ell_d = _parse_maximal_feasible_tuple(m, cert["ell_delta_m"], "ell_delta_m")
    ell_sp = _parse_maximal_feasible_tuple(mp, cert["ell_star_m_prime"], "ell_star_m_prime")

    def _is_rob(anch: Fraction, tup: List[Fraction], eps: Fraction) -> bool:
        pcs = six_pieces_from_anchor(anch, tup)
        v54 = [
            [eval_pw_const_valuation_q(bp, dens[i], pcs[f"P{j+1}"][0], pcs[f"P{j+1}"][1]) for j in range(4)]
            for i in range(5)
        ]
        ok, _ = check_hall_leaving_agent_robustness(delta_favourite_graph(v54, eps))
        return ok

    if not _is_rob(m, ell_s, Fraction(0, 1)):
        raise Cake5CertificateError("ell_star_m is NOT 0-robust at anchor_m")
    if not _is_rob(m, ell_d, delta):
        raise Cake5CertificateError("ell_delta_m is NOT delta-robust at anchor_m")
    if not _is_rob(mp, ell_sp, Fraction(0, 1)):
        raise Cake5CertificateError("ell_star_m_prime is NOT 0-robust at anchor_m_prime")

    stab_linf = max(abs(a - b) for a, b in zip(ell_d, ell_s))
    inv_g3 = Fraction(1, 1) / (gamma * gamma * gamma)
    lem317_ub = Fraction(3, 1) * inv_g3 * delta
    if stab_linf > lem317_ub:
        raise Cake5CertificateError(f"Lemma 3.17 violated: ||ell - ell*||_inf={stab_linf} > {lem317_ub}")

    shift_d = abs(m - mp)
    lip_linf = max(abs(a - b) for a, b in zip(ell_s, ell_sp))
    lem318_ub = Fraction(13, 1) * inv_g3 * shift_d
    if lip_linf > lem318_ub:
        raise Cake5CertificateError(f"Lemma 3.18 violated: ||ell*(m) - ell*(m')||_inf={lip_linf} > {lem318_ub}")

    if _parse_rat(cert["claimed_stability_linf"], "claimed_stability_linf") != stab_linf:
        raise Cake5CertificateError("claimed_stability_linf mismatch")
    if _parse_rat(cert["claimed_lemma317_bound"], "claimed_lemma317_bound") != lem317_ub:
        raise Cake5CertificateError("claimed_lemma317_bound mismatch")
    if _parse_rat(cert["claimed_anchor_shift_d"], "claimed_anchor_shift_d") != shift_d:
        raise Cake5CertificateError("claimed_anchor_shift_d mismatch")
    if _parse_rat(cert["claimed_lipschitz_linf"], "claimed_lipschitz_linf") != lip_linf:
        raise Cake5CertificateError("claimed_lipschitz_linf mismatch")
    if _parse_rat(cert["claimed_lemma318_bound"], "claimed_lemma318_bound") != lem318_ub:
        raise Cake5CertificateError("claimed_lemma318_bound mismatch")

    return {
        "verified": True,
        "mode": cert["mode"],
        "stab_linf": format_rat(stab_linf),
        "lip_linf": format_rat(lip_linf),
    }


# =============================================================================
# Mode 4: Theorems 1 & 2 Complete 5-Agent Contiguous EF / eps-EF Certificate
# =============================================================================


def _verify_mode4_complete_ef5(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema",
        "mode",
        "cert_id",
        "valuations",
        "anchor_m",
        "ell_tuple",
        "target_eps",
        "fifth_piece_name",
        "allocation_5",
        "spanning_tree_edges",
        "claimed_max_envy",
        "claimed_total_length",
        "claimed_tree_valid",
        "claimed_eps_ef_verified",
    }
    _parse_exact_keys(cert, req, "Mode 4")
    bp, dens = _parse_valuations_5(cert["valuations"])
    m = _parse_rat(cert["anchor_m"], "anchor_m")
    ell = _parse_maximal_feasible_tuple(m, cert["ell_tuple"], "ell_tuple")
    eps = _parse_rat(cert["target_eps"], "target_eps")
    if eps < Fraction(0, 1):
        raise Cake5CertificateError("target_eps must be >= 0")

    fifth = cert["fifth_piece_name"]
    if fifth not in ("L", "R"):
        raise Cake5CertificateError("fifth_piece_name must be 'L' or 'R'")
    pcs = six_pieces_from_anchor(m, ell)
    other = "R" if fifth == "L" else "L"
    if pcs[other][1] - pcs[other][0] != Fraction(0, 1):
        raise Cake5CertificateError(f"Unassigned gap {other} is non-empty (allocation incomplete)")

    active_names = ["P1", "P2", "P3", "P4", fifth]
    active_intervals = [pcs[nm] for nm in active_names]
    total_len = sum((b - a for a, b in active_intervals), Fraction(0, 1))
    if total_len != Fraction(1, 1):
        raise Cake5CertificateError(f"Allocated pieces total length {total_len} != 1")

    raw_alloc = cert["allocation_5"]
    if type(raw_alloc) is not list or len(raw_alloc) != 5:
        raise Cake5CertificateError("allocation_5 must list 5 piece names")
    if not all(type(x) is str for x in raw_alloc) or sorted(raw_alloc) != sorted(active_names):
        raise Cake5CertificateError("allocation_5 must be a bijection onto active 5 pieces")

    # Compute exact 5x5 valuation matrix and exact max additive envy across all 25 pairs
    val_map: List[Dict[str, Fraction]] = []
    max_envy = Fraction(0, 1)
    for i in range(5):
        vdict = {nm: eval_pw_const_valuation_q(bp, dens[i], pcs[nm][0], pcs[nm][1]) for nm in active_names}
        val_map.append(vdict)
        own = vdict[raw_alloc[i]]
        for nm in active_names:
            diff = vdict[nm] - own
            if diff > max_envy:
                max_envy = diff
    if max_envy > eps:
        raise Cake5CertificateError(f"Max additive envy {max_envy} > target_eps {eps}")

    # Verify spanning tree witness T is a valid 8-edge spanning tree of G_eps(m, ell) (Lemma 4.2)!
    vals_5x4 = [[val_map[i][f"P{j+1}"] for j in range(4)] for i in range(5)]
    adj_eps = delta_favourite_graph(vals_5x4, eps)
    raw_tree = cert["spanning_tree_edges"]
    if type(raw_tree) is not list or len(raw_tree) != 8:
        raise Cake5CertificateError("spanning_tree_edges must have 8 edges")
    t_edges: List[Tuple[int, int]] = []
    for ei, e in enumerate(raw_tree):
        if type(e) is not list or len(e) != 2:
            raise Cake5CertificateError(f"spanning_tree_edges[{ei}] must be [agent, piece]")
        t_edges.append((_parse_int(e[0], "agent"), _parse_int(e[1], "piece")))
    if not check_spanning_tree_5x4(t_edges, adj_eps):
        raise Cake5CertificateError("spanning_tree_edges is NOT a valid spanning tree of G_eps(m, ell)")

    if _parse_rat(cert["claimed_max_envy"], "claimed_max_envy") != max_envy:
        raise Cake5CertificateError("claimed_max_envy mismatch")
    if _parse_rat(cert["claimed_total_length"], "claimed_total_length") != total_len:
        raise Cake5CertificateError("claimed_total_length mismatch")
    if cert["claimed_tree_valid"] is not True or cert["claimed_eps_ef_verified"] is not True:
        raise Cake5CertificateError("claimed_tree_valid and claimed_eps_ef_verified must be true")

    return {
        "verified": True,
        "mode": cert["mode"],
        "max_envy": format_rat(max_envy),
        "target_eps": format_rat(eps),
        "fifth_piece": fifth,
    }


def verify_cake5_certificate_exact(cert: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level zero-float entry point for EF-CAKE5-CERT-1.0."""
    if type(cert) is not dict:
        raise Cake5CertificateError("Certificate root must be a JSON object")
    _assert_strict_json_types(cert)
    if cert.get("schema") != SCHEMA_VERSION:
        raise Cake5CertificateError(f"Unsupported schema: {cert.get('schema')!r}")
    cid = cert.get("cert_id")
    if type(cid) is not str or not (1 <= len(cid) <= MAX_ID_LEN):
        raise Cake5CertificateError(f"cert_id must be string of length in [1, {MAX_ID_LEN}]")
    mode = cert.get("mode")
    if mode == "hall_robust_connectivity_lemma34_35_cert":
        return _verify_mode1_hall_robust(cert)
    if mode == "softmax_weight_balance_lemma39_cert":
        return _verify_mode2_softmax_balance(cert)
    if mode == "stability_and_lipschitz_lemma317_318_cert":
        return _verify_mode3_stability_lipschitz(cert)
    if mode == "complete_ef5_allocation_theorem1_2_cert":
        return _verify_mode4_complete_ef5(cert)
    raise Cake5CertificateError(f"Unknown verification mode: {mode!r}")
