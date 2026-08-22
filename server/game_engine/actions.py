"""Legal-action generation from a private hand."""

from __future__ import annotations

from itertools import combinations

from .cards import RANK_VALUE, card_rank, sort_cards
from .patterns import CardPattern, InvalidAction, classify_cards, compare_plays


def _windows(ranks: list[str], minimum: int):
    values = [RANK_VALUE[r] for r in ranks if RANK_VALUE[r] <= RANK_VALUE["A"]]
    for length in range(minimum, len(values) + 1):
        for start in range(len(values) - length + 1):
            part = values[start : start + length]
            if part == list(range(part[0], part[0] + length)):
                yield [next(r for r, value in RANK_VALUE.items() if value == v) for v in part]


def generate_plays(hand, incumbent: CardPattern | None = None) -> list[tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for card in sort_cards(hand):
        grouped.setdefault(card_rank(card), []).append(card)
    ranks = sorted(grouped, key=RANK_VALUE.get)
    candidates: set[tuple[str, ...]] = set()

    def add(cards):
        ordered = tuple(sort_cards(cards))
        try:
            pattern = classify_cards(ordered)
        except InvalidAction:
            return
        if incumbent is None or compare_plays(pattern, incumbent):
            candidates.add(ordered)

    for rank in ranks:
        cards = grouped[rank]
        add(cards[:1])
        if len(cards) >= 2:
            add(cards[:2])
        if len(cards) >= 3:
            add(cards[:3])
            remainder = [c for r in ranks if r != rank for c in grouped[r]]
            for wing in remainder:
                add(cards[:3] + [wing])
            for pair_rank in ranks:
                if pair_rank != rank and len(grouped[pair_rank]) >= 2:
                    add(cards[:3] + grouped[pair_rank][:2])
        if len(cards) == 4:
            add(cards)
            remainder = [c for r in ranks if r != rank for c in grouped[r]]
            for wings in combinations(remainder, 2):
                add(cards + list(wings))
            pair_ranks = [r for r in ranks if r != rank and len(grouped[r]) >= 2]
            for pair_wings in combinations(pair_ranks, 2):
                add(cards + grouped[pair_wings[0]][:2] + grouped[pair_wings[1]][:2])
    if "BJ" in grouped and "RJ" in grouped:
        add([grouped["BJ"][0], grouped["RJ"][0]])

    single_ranks = [r for r in ranks if grouped[r]]
    for window in _windows(single_ranks, 5):
        add([grouped[r][0] for r in window])
    pair_ranks = [r for r in ranks if len(grouped[r]) >= 2]
    for window in _windows(pair_ranks, 3):
        add([c for r in window for c in grouped[r][:2]])
    triple_ranks = [r for r in ranks if len(grouped[r]) >= 3]
    for core in _windows(triple_ranks, 2):
        base = [c for r in core for c in grouped[r][:3]]
        add(base)
        remainder = [c for r in ranks if r not in core for c in grouped[r]]
        for wings in combinations(remainder, len(core)):
            add(base + list(wings))
        wing_pair_ranks = [r for r in ranks if r not in core and len(grouped[r]) >= 2]
        for wing_ranks in combinations(wing_pair_ranks, len(core)):
            add(base + [c for r in wing_ranks for c in grouped[r][:2]])

    return sorted(candidates, key=lambda cards: (len(cards), classify_cards(cards).kind, classify_cards(cards).main_rank, cards))

