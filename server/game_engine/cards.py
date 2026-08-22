"""Card primitives for a standard 54-card Dou Dizhu deck."""

from __future__ import annotations

from collections import Counter

RANKS = ("3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2", "BJ", "RJ")
SUITS = ("S", "H", "C", "D")
RANK_VALUE = {rank: value for value, rank in enumerate(RANKS)}


def make_deck() -> list[str]:
    return [f"{rank}{suit}" for rank in RANKS[:-2] for suit in SUITS] + ["BJ", "RJ"]


def card_rank(card: str) -> str:
    if card in ("BJ", "RJ"):
        return card
    rank, suit = card[:-1], card[-1]
    if rank not in RANK_VALUE or suit not in SUITS:
        raise ValueError(f"invalid card: {card}")
    return rank


def card_key(card: str) -> tuple[int, int]:
    rank = card_rank(card)
    return RANK_VALUE[rank], SUITS.index(card[-1]) if rank not in ("BJ", "RJ") else 0


def sort_cards(cards) -> list[str]:
    return sorted(cards, key=card_key)


def rank_counts(cards) -> Counter[str]:
    return Counter(card_rank(card) for card in cards)

