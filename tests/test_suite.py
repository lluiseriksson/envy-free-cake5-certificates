"""Comprehensive pytest & 60-attack live adversarial red-team suite for Paper 45:
EF-CAKE5-CERT-1.0 (Filos-Ratsikas, Hollender, Latifian, & Tyrovolas, arXiv:2611.33149).

Author: Lluis Eriksson
License: MIT
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cake5_certifier import Cake5CertificateError, verify_cake5_certificate_exact

CERT_DIR = ROOT / "certificates"


def _load(name: str) -> Dict[str, Any]:
    return json.loads((CERT_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_all_16_canonical_certificates_verify() -> None:
    paths = sorted(CERT_DIR.glob("*.json"))
    assert len(paths) == 16, f"Expected 16 certificates, found {len(paths)}"
    for p in paths:
        res = verify_cake5_certificate_exact(json.loads(p.read_text(encoding="utf-8")))
        assert res["verified"] is True


def _mut(base: Dict[str, Any], fn: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
    c = copy.deepcopy(base)
    fn(c)
    return c


def build_60_adversarial_attacks() -> List[Tuple[str, Any]]:
    m1 = _load("m1_hall_exact_0rob_right_gap")
    m2 = _load("m2_softmax_sharp_cap_1_32")
    m3 = _load("m3_stab_lip_uniform_g1")
    m4 = _load("m4_ef5_exact_0envy_right_gap")

    attacks: List[Tuple[str, Any]] = [
        # --- Global Schema / Type / Rational / Depth Hardening (12 attacks) ---
        ("g01_non_dict_root", [1, 2, 3]),
        ("g02_wrong_schema", _mut(m1, lambda c: c.__setitem__("schema", "EF-CAKE5-CERT-2.0"))),
        ("g03_empty_cert_id", _mut(m1, lambda c: c.__setitem__("cert_id", ""))),
        ("g04_unknown_mode", _mut(m1, lambda c: c.__setitem__("mode", "bogus"))),
        ("g05_float_leak", _mut(m1, lambda c: c.__setitem__("anchor_m", 0.4))),
        ("g06_none_injection", _mut(m1, lambda c: c.__setitem__("delta", None))),
        ("g07_bool_as_int", _mut(m1, lambda c: c.__setitem__("claimed_fav_graph_edge_count", True))),
        ("g08_unreduced_fraction", _mut(m1, lambda c: c.__setitem__("anchor_m", "4/10"))),
        ("g09_den_one_fraction", _mut(m3, lambda c: c.__setitem__("gamma_hungry", "1/1"))),
        ("g10_trailing_newline_rat", _mut(m1, lambda c: c.__setitem__("anchor_m", "2/5\n"))),
        ("g11_oversized_rat_str", _mut(m1, lambda c: c.__setitem__("anchor_m", "1/" + "9" * 1200))),
        ("g12_json_depth_dos", _mut(m1, lambda c: c.__setitem__("ell_tuple", eval("[" * 40 + "0" + "]" * 40)))),
        # --- Mode 1: Lemmas 3.4-3.5 Leaving-Agent Hall Robustness (12 attacks) ---
        ("m1_01_extra_key", _mut(m1, lambda c: c.__setitem__("extra", 1))),
        ("m1_02_non_maximal_tuple", _mut(m1, lambda c: c["ell_tuple"].__setitem__(0, "1/10"))),
        ("m1_03_infeasible_tuple", _mut(m1, lambda c: c["ell_tuple"].__setitem__(0, "3/10"))),
        ("m1_04_density_gt_1", _mut(m1, lambda c: c["valuations"]["densities_5"][0].__setitem__(0, "3/2"))),
        ("m1_05_negative_delta", _mut(m1, lambda c: c.__setitem__("delta", "-1/10"))),
        ("m1_06_not_delta_robust", _mut(m1, lambda c: c["ell_tuple"].__setitem__(2, "3/10"))),
        ("m1_07_non_perm_matching", _mut(m1, lambda c: c["claimed_leaving_matchings"][0].__setitem__(0, 3))),
        ("m1_08_non_fav_matching", _mut(m1, lambda c: c.__setitem__("claimed_leaving_matchings", [[2, 0, 1, 3]] * 5))),
        ("m1_09_wrong_empty_gap", _mut(m1, lambda c: c.__setitem__("claimed_empty_gap", "R"))),
        ("m1_10_wrong_edge_count", _mut(m1, lambda c: c.__setitem__("claimed_fav_graph_edge_count", 1))),
        ("m1_11_robust_false", _mut(m1, lambda c: c.__setitem__("claimed_is_delta_robust", False))),
        ("m1_12_connected_false", _mut(m1, lambda c: c.__setitem__("claimed_is_connected", False))),
        # --- Mode 2: Lemmas 3.7 & 3.9 Softmax Weight Balance (12 attacks) ---
        ("m2_01_extra_key", _mut(m2, lambda c: c.__setitem__("extra", 1))),
        ("m2_02_agent_sum_not_one", _mut(m2, lambda c: c["weights_5x4"][0].__setitem__(0, "1/2"))),
        ("m2_03_negative_weight", _mut(m2, lambda c: (c["weights_5x4"][0].__setitem__(2, "-1/32"), c["weights_5x4"][0].__setitem__(0, "17/32")))),
        ("m2_04_nonfav_exceeds_1_32", _mut(m2, lambda c: (c["weights_5x4"][0].__setitem__(2, "1/16"), c["weights_5x4"][0].__setitem__(0, "7/16")))),
        ("m2_05_int_as_bool_fav_mask", _mut(m2, lambda c: c["fav_mask_5x4"][0].__setitem__(0, 1))),
        ("m2_06_piece_total_not_5_4", _mut(m2, lambda c: (c["weights_5x4"][4].__setitem__(0, "3/8"), c["weights_5x4"][4].__setitem__(1, "1/8")))),
        ("m2_07_empty_fav_row", _mut(m2, lambda c: c.__setitem__("fav_mask_5x4", [[False] * 4] + c["fav_mask_5x4"][1:]))),
        ("m2_08_wrong_piece_totals", _mut(m2, lambda c: c["claimed_piece_totals"].__setitem__(0, "1"))),
        ("m2_09_wrong_max_nonfav", _mut(m2, lambda c: c.__setitem__("claimed_max_nonfav_weight", "0"))),
        ("m2_10_wrong_min_fav_counts", _mut(m2, lambda c: c["claimed_subset_min_fav_agents"].__setitem__(0, 1))),
        ("m2_11_hall_false", _mut(m2, lambda c: c.__setitem__("claimed_hall_satisfied", False))),
        ("m2_12_wrong_row_len", _mut(m2, lambda c: c["weights_5x4"][0].pop())),
        # --- Mode 3: Lemmas 3.17 & 3.18 Stability & Lipschitz Continuity (12 attacks) ---
        ("m3_01_extra_key", _mut(m3, lambda c: c.__setitem__("extra", 1))),
        ("m3_02_gamma_zero", _mut(m3, lambda c: c.__setitem__("gamma_hungry", "0"))),
        ("m3_03_hungry_violated", _mut(m3, lambda c: c["valuations"]["densities_5"][0].__setitem__(0, "1/2"))),
        ("m3_04_delta_zero", _mut(m3, lambda c: c.__setitem__("delta", "0"))),
        ("m3_05_same_anchors", _mut(m3, lambda c: c.__setitem__("anchor_m_prime", c["anchor_m"]))),
        ("m3_06_ell_star_not_0rob", _mut(m3, lambda c: c.__setitem__("ell_star_m", ["21/100", "19/100", "1/5", "1/5"]))),
        ("m3_07_ell_delta_not_drob", _mut(m3, lambda c: c.__setitem__("delta", "1/1000"))),
        ("m3_08_wrong_stab_linf", _mut(m3, lambda c: c.__setitem__("claimed_stability_linf", "0"))),
        ("m3_09_wrong_lem317_ub", _mut(m3, lambda c: c.__setitem__("claimed_lemma317_bound", "1"))),
        ("m3_10_wrong_anchor_shift", _mut(m3, lambda c: c.__setitem__("claimed_anchor_shift_d", "1/10"))),
        ("m3_11_wrong_lip_linf", _mut(m3, lambda c: c.__setitem__("claimed_lipschitz_linf", "0"))),
        ("m3_12_wrong_lem318_ub", _mut(m3, lambda c: c.__setitem__("claimed_lemma318_bound", "1"))),
        # --- Mode 4: Theorems 1 & 2 Complete 5-Agent Contiguous EF / eps-EF (12 attacks) ---
        ("m4_01_extra_key", _mut(m4, lambda c: c.__setitem__("extra", 1))),
        ("m4_02_bad_fifth_piece", _mut(m4, lambda c: c.__setitem__("fifth_piece_name", "P5"))),
        ("m4_03_wrong_empty_gap_assign", _mut(m4, lambda c: c.__setitem__("fifth_piece_name", "L"))),
        ("m4_04_duplicate_piece_alloc", _mut(m4, lambda c: c["allocation_5"].__setitem__(1, "P1"))),
        ("m4_05_envy_exceeds_eps", _mut(m4, lambda c: c.__setitem__("allocation_5", ["P3", "P4", "P1", "P2", "R"]))),
        ("m4_06_negative_eps", _mut(m4, lambda c: c.__setitem__("target_eps", "-1/10"))),
        ("m4_07_tree_too_few_edges", _mut(m4, lambda c: c["spanning_tree_edges"].pop())),
        ("m4_08_tree_has_cycle", _mut(m4, lambda c: c["spanning_tree_edges"].__setitem__(0, c["spanning_tree_edges"][1]))),
        ("m4_09_wrong_max_envy", _mut(m4, lambda c: c.__setitem__("claimed_max_envy", "1/10"))),
        ("m4_10_wrong_total_len", _mut(m4, lambda c: c.__setitem__("claimed_total_length", "4/5"))),
        ("m4_11_tree_valid_false", _mut(m4, lambda c: c.__setitem__("claimed_tree_valid", False))),
        ("m4_12_ef_verified_false", _mut(m4, lambda c: c.__setitem__("claimed_eps_ef_verified", False))),
    ]
    assert len(attacks) == 60
    return attacks


def test_60_live_adversarial_attacks_rejected() -> None:
    attacks = build_60_adversarial_attacks()
    rejected = 0
    for name, payload in attacks:
        try:
            verify_cake5_certificate_exact(payload)
        except Cake5CertificateError:
            rejected += 1
        else:
            raise AssertionError(f"Adversarial attack {name!r} was NOT rejected!")
    assert rejected == 60


def test_exact_no_float_source_audit() -> None:
    for rel in ["src/cake5_exact.py", "src/cake5_certifier.py"]:
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert "float(" not in src, f"float() found in {rel}"
        assert "math." not in src, f"math. found in {rel}"
        assert "numpy" not in src, f"numpy found in {rel}"
