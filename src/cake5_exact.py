"""Zero-floating-point exact-Q primitives for Paper 45:
Aris Filos-Ratsikas, Alexandros Hollender, Mohamad Latifian, & Giannis Tyrovolas
(arXiv:2611.33149, Nov 24, 2026) "Envy-Free Cake-Cutting for Five Agents".

Strict rule: zero floating-point arithmetic — Python fractions.Fraction only.

Author: Lluis Eriksson
License: MIT
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Sequence, Set, Tuple


def format_rat(q: Fraction) -> str:
    """Canonical reduced rational string ('n' if den == 1 else 'n/d')."""
    if q.denominator == 1:
        return str(q.numerator)
    return f"{q.numerator}/{q.denominator}"


def eval_pw_const_valuation_q(
    breakpoints: Sequence[Fraction],
    densities: Sequence[Fraction],
    left: Fraction,
    right: Fraction,
) -> Fraction:
    """Exact integral of piecewise-constant valuation density over [left, right] subset [0, 1].
    breakpoints: [0 = b_0 < b_1 < ... < b_K = 1], densities: [d_0, ..., d_{K-1}] >= 0.
    """
    if left >= right:
        return Fraction(0, 1)
    total = Fraction(0, 1)
    for idx in range(len(densities)):
        a = breakpoints[idx]
        b = breakpoints[idx + 1]
        lo = left if left > a else a
        hi = right if right < b else b
        if hi > lo:
            total += densities[idx] * (hi - lo)
    return total


def six_pieces_from_anchor(
    m: Fraction, ell: Sequence[Fraction]
) -> Dict[str, Tuple[Fraction, Fraction]]:
    """Definition 3.1 six contiguous pieces:
      P1 = [0, l1], L = [l1, m - l2], P2 = [m - l2, m],
      P3 = [m, m + l3], R = [m + l3, 1 - l4], P4 = [1 - l4, 1].
    """
    l1, l2, l3, l4 = ell[0], ell[1], ell[2], ell[3]
    return {
        "P1": (Fraction(0, 1), l1),
        "L": (l1, m - l2),
        "P2": (m - l2, m),
        "P3": (m, m + l3),
        "R": (m + l3, Fraction(1, 1) - l4),
        "P4": (Fraction(1, 1) - l4, Fraction(1, 1)),
    }


def delta_favourite_graph(
    vals_5x4: Sequence[Sequence[Fraction]],
    delta: Fraction,
) -> List[List[int]]:
    """Definition 3.3 bipartite graph G_delta(m, ell) on [5] x [4]:
    edge (i, j) iff v_i(P_j) + delta >= max_{k in [4]} v_i(P_k).
    Returns adjacency list adj[i] = sorted list of favourite piece indices j in 0..3.
    """
    adj: List[List[int]] = []
    for i in range(5):
        mx = max(vals_5x4[i])
        adj.append([j for j in range(4) if vals_5x4[i][j] + delta >= mx])
    return adj


def check_hall_leaving_agent_robustness(adj: Sequence[Sequence[int]]) -> Tuple[bool, List[List[int]]]:
    """Lemma 3.4 exact Hall check for all 5 departing agents i in 0..4 and all subsets S subset [5]\\{i},
    plus explicit backtracking perfect matchings M_i: [5]\\{i} -> [4] (returned as 5 lists of 4 pairs).
    """
    matchings: List[List[int]] = []
    for leave in range(5):
        rem = [a for a in range(5) if a != leave]
        # Exhaustive Hall subset check over all 16 subsets of rem
        for mask in range(1, 16):
            S = [rem[k] for k in range(4) if (mask >> k) & 1]
            nbrs: Set[int] = set()
            for a in S:
                nbrs.update(adj[a])
            if len(nbrs) < len(S):
                return False, []
        # Find explicit perfect matching (piece assigned to each agent in rem)
        found: List[int] | None = None

        def bt(pos: int, used: int, cur: List[int]) -> None:
            nonlocal found
            if found is not None:
                return
            if pos == 4:
                found = list(cur)
                return
            a = rem[pos]
            for j in adj[a]:
                if not ((used >> j) & 1):
                    cur.append(j)
                    bt(pos + 1, used | (1 << j), cur)
                    cur.pop()

        bt(0, 0, [])
        if found is None:
            return False, []
        matchings.append(found)
    return True, matchings


def is_bipartite_connected_5x4(adj: Sequence[Sequence[int]]) -> bool:
    """Lemma 3.5 exact BFS connectivity test on bipartite graph [5] U [4] (9 vertices)."""
    # Vertices 0..4 = agents, 5..8 = pieces
    g: List[List[int]] = [[] for _ in range(9)]
    for i in range(5):
        for j in adj[i]:
            g[i].append(5 + j)
            g[5 + j].append(i)
    seen = {0}
    queue = [0]
    while queue:
        u = queue.pop()
        for w in g[u]:
            if w not in seen:
                seen.add(w)
                queue.append(w)
    return len(seen) == 9


def check_spanning_tree_5x4(edges: Sequence[Tuple[int, int]], adj: Sequence[Sequence[int]]) -> bool:
    """Verify that `edges` (pairs (agent i in 0..4, piece j in 0..3)) is an 8-edge spanning tree
    of the 9-vertex bipartite graph G_delta(m, ell)."""
    if len(edges) != 8:
        return False
    seen_e: Set[Tuple[int, int]] = set()
    g: List[List[int]] = [[] for _ in range(9)]
    for i, j in edges:
        if not (0 <= i < 5 and 0 <= j < 4):
            return False
        if j not in adj[i] or (i, j) in seen_e:
            return False
        seen_e.add((i, j))
        g[i].append(5 + j)
        g[5 + j].append(i)
    # 8 edges on 9 vertices is a spanning tree iff connected!
    seen = {0}
    q = [0]
    while q:
        u = q.pop()
        for w in g[u]:
            if w not in seen:
                seen.add(w)
                q.append(w)
    return len(seen) == 9
