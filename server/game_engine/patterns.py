"""Original, dependency-free Dou Dizhu play classification and comparison."""

from __future__ import annotations

from dataclasses import dataclass

from .cards import RANK_VALUE, card_rank, rank_counts


class InvalidAction(ValueError):
    """An action is malformed, stale, out of turn, or illegal."""


@dataclass(frozen=True)
class CardPattern:
    kind: str
    main_rank: int
    sequence_length: int = 1
    card_count: int = 1


def _consecutive(values: list[int]) -> bool:
    return bool(values) and values == list(range(values[0], values[0] + len(values)))


def _airplane(counts, total: int) -> CardPattern | None:
    eligible = sorted(RANK_VALUE[r] for r, n in counts.items() if n >= 3 and RANK_VALUE[r] <= RANK_VALUE["A"])
    for length in range(len(eligible), 1, -1):
        for start in range(len(eligible) - length + 1):
            core = eligible[start : start + length]
            if not _consecutive(core):
                continue
            remainder = dict(counts)
            for value in core:
                rank = next(r for r, v in RANK_VALUE.items() if v == value)
                remainder[rank] -= 3
            residual = [n for n in remainder.values() if n]
            if total == 3 * length and not residual:
                return CardPattern("airplane", core[-1], length, total)
            if total == 4 * length and sum(residual) == length:
                return CardPattern("airplane_single", core[-1], length, total)
            if total == 5 * length and len(residual) == length and all(n == 2 for n in residual):
                return CardPattern("airplane_pair", core[-1], length, total)
    return None


def classify_cards(cards) -> CardPattern:
    cards = tuple(cards)
    if not cards:
        raise InvalidAction("a play cannot be empty")
    try:
        counts = rank_counts(cards)
    except ValueError as exc:
        raise InvalidAction(str(exc)) from exc
    if sum(counts.values()) != len(cards) or any(n > (1 if r in ("BJ", "RJ") else 4) for r, n in counts.items()):
        raise InvalidAction("cards do not form a physical deck subset")
    n = len(cards)
    values = sorted(RANK_VALUE[r] for r in counts)
    multiplicities = sorted(counts.values(), reverse=True)
    high = max(values)

    if n == 2 and set(counts) == {"BJ", "RJ"}:
        return CardPattern("rocket", RANK_VALUE["RJ"], card_count=2)
    if n == 4 and multiplicities == [4]:
        return CardPattern("bomb", high, card_count=4)
    if n == 1:
        return CardPattern("single", high)
    if n == 2 and multiplicities == [2]:
        return CardPattern("pair", high, card_count=2)
    if n == 3 and multiplicities == [3]:
        return CardPattern("triple", high, card_count=3)
    triple_rank = next((RANK_VALUE[r] for r, count in counts.items() if count == 3), None)
    if n == 4 and multiplicities == [3, 1]:
        return CardPattern("triple_single", triple_rank, card_count=4)
    if n == 5 and multiplicities == [3, 2]:
        return CardPattern("triple_pair", triple_rank, card_count=5)
    if n >= 5 and all(x == 1 for x in counts.values()) and high <= RANK_VALUE["A"] and _consecutive(values):
        return CardPattern("straight", high, len(values), n)
    if n >= 6 and n % 2 == 0 and all(x == 2 for x in counts.values()) and high <= RANK_VALUE["A"] and _consecutive(values):
        return CardPattern("pair_straight", high, len(values), n)
    airplane = _airplane(counts, n)
    if airplane:
        return airplane
    quad_rank = next((RANK_VALUE[r] for r, count in counts.items() if count == 4), None)
    if n == 6 and quad_rank is not None:
        return CardPattern("four_two_single", quad_rank, card_count=6)
    if n == 8 and quad_rank is not None:
        remainder = [count for rank, count in counts.items() if RANK_VALUE[rank] != quad_rank]
        if len(remainder) == 2 and all(count == 2 for count in remainder):
            return CardPattern("four_two_pair", quad_rank, card_count=8)
    raise InvalidAction(f"illegal card combination: {cards}")


def compare_plays(candidate: CardPattern, incumbent: CardPattern) -> bool:
    if candidate.kind == "rocket":
        return incumbent.kind != "rocket"
    if incumbent.kind == "rocket":
        return False
    if candidate.kind == "bomb" and incumbent.kind != "bomb":
        return True
    if incumbent.kind == "bomb" and candidate.kind != "bomb":
        return False
    return (
        candidate.kind == incumbent.kind
        and candidate.card_count == incumbent.card_count
        and candidate.sequence_length == incumbent.sequence_length
        and candidate.main_rank > incumbent.main_rank
    )

