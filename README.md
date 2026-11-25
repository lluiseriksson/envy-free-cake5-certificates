# Certified Verification of Envy-Free Cake-Cutting for Five Agents

[![License: MIT](https://img.shields.io/badge/Code%20%26%20Lean-MIT-blue.svg)](LICENSE)
[![Paper License: CC-BY-4.0](https://img.shields.io/badge/Paper-CC--BY--4.0-green.svg)](paper/main.tex)

**Author:** Lluis Eriksson

Machine-checked **Lean 4.35.0** formalization and zero-floating-point exact-$\mathbb{Q}$ certificate audit (`EF-CAKE5-CERT-1.0`) for **Aris Filos-Ratsikas, Alexandros Hollender, Mohamad Latifian, & Giannis Tyrovolas** ([arXiv:2611.33149](https://arxiv.org/abs/2611.33149), Nov 24, 2026), *"Envy-Free Cake-Cutting for Five Agents"*.

---

## Key Verified Artifacts

| Artifact | Verification Metric | Result |
| :--- | :--- | :--- |
| **Lean 4.35.0 Kernel** (`lean/EnvyFreeCake5.lean`) | 18 theorems, zero `sorry`, zero warnings, zero `Classical.choice` | **18 / 18 PASS** (`2` `none`, `16` `[propext, Quot.sound]`) |
| **Exact-$\mathbb{Q}$ Verifier** (`src/cake5_certifier.py`) | Zero `float()`, `math`, or `numpy`; 4-mode `EF-CAKE5-CERT-1.0` | **16 / 16 PASS** (`0.246–0.934 ms`, total `7.80 ms`) |
| **Adversarial Red-Team Suite** (`tests/test_suite.py`) | 60 live forged payloads (12 global + 12/mode) | **60 / 60 REJECTED** |
| **SHA-256 Integrity Manifest** (`SHA256_MANIFEST.json`) | Full deterministic replay check (`scripts/verify_all.py`) | **41 / 41 MATCH** |
| **Manuscript** (`paper/main.pdf`) | 3 pages, 3 publication figures (`300 DPI`) | **0 warnings, 0 overfulls** |

---

## Four Certificate Modes (`EF-CAKE5-CERT-1.0`)

1. **`hall_robust_connectivity_lemma34_35_cert` (Mode 1 — Defs. 3.1–3.3 & Lemmas 3.4–3.5):** Audits maximal feasible 4-tuples $(\ell_1, \ell_2, \ell_3, \ell_4)$ at anchor $m \in [0, 1]$ under exact piecewise-constant 1-Lipschitz valuations, constructs $G_\delta(m, \ell)$, checks leaving-agent Hall's condition across all 5 departing agents and all 16 subsets, verifies Lemma 3.5 connectivity, and checks explicit witness perfect matchings.
2. **`softmax_weight_balance_lemma39_cert` (Mode 2 — Lemmas 3.7 & 3.9):** Audits exact rational weight tables $w_{ij} \ge 0$ ($\sum_j w_{ij} = 1$, $W_j = 5/4$, non-favourite weights $\le 2^{-5} = 1/32$), verifying Lemma 3.9's Hall margin across all 15 non-empty piece subsets and induced $\delta$-robustness.
3. **`stability_and_lipschitz_lemma317_318_cert` (Mode 3 — Lemmas 3.17 & 3.18):** Audits exact 0-robust and $\delta$-robust maximal feasible tuples across $\gamma$-strongly hungry valuations at anchors $m \ne m'$, certifying $|\ell_i - \ell_i^*(m)| \le 3\gamma^{-3}\delta$ and $|\ell_i^*(m) - \ell_i^*(m')| \le 13\gamma^{-3}|m - m'|$.
4. **`complete_ef5_allocation_theorem1_2_cert` (Mode 4 — Theorems 1 & 2):** Certifies complete 5-agent contiguous allocations $(P_1, P_2, P_3, P_4, L\text{ or }R)$ covering $[0, 1]$ with zero unused cake, exact max additive envy $\le \varepsilon$ across all 25 pairs, and a valid 8-edge spanning tree $T \subseteq G_\varepsilon(m, \ell)$ (Lemma 4.2).

---

## Quick Reproduction

```bash
cd lean && lake build && lake env lean AuditAxioms.lean && cd ..
python scripts/run_all_experiments.py
python scripts/make_figures.py
python scripts/verify_all.py
```

---

## Licenses & Transparency Disclosure

- **Code, Lean proofs, certificates, and scripts:** [MIT License](LICENSE).
- **Manuscript (`paper/main.tex`, `paper/main.pdf`) and figures:** CC-BY-4.0.
- **AI Assistance Disclosure:** Prepared by sole author Lluis Eriksson with AI coding, formalization, and drafting assistance from Google Antigravity; all Lean proofs, exact-$\mathbb{Q}$ certificates, and adversarial tests were independently compiled and machine-verified locally.
