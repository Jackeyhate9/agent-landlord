import pytest

from server.game_engine import CardPattern, InvalidAction, classify_cards, compare_plays


def test_classifies_all_required_families():
    cases = {
        ("3S",): "single",
        ("3S", "3H"): "pair",
        ("4S", "4H", "4C"): "triple",
        ("4S", "4H", "4C", "7D"): "triple_single",
        ("4S", "4H", "4C", "7D", "7C"): "triple_pair",
        ("3S", "4H", "5C", "6D", "7S"): "straight",
        ("3S", "3H", "4S", "4H", "5S", "5H"): "pair_straight",
        ("3S", "3H", "3C", "4S", "4H", "4C"): "airplane",
        ("3S", "3H", "3C", "4S", "4H", "4C", "7D", "8D"): "airplane_single",
        ("3S", "3H", "3C", "4S", "4H", "4C", "7D", "7C", "8D", "8C"): "airplane_pair",
        ("6S", "6H", "6C", "6D", "7S", "8H"): "four_two_single",
        ("6S", "6H", "6C", "6D", "7S", "7H", "8S", "8H"): "four_two_pair",
        ("9S", "9H", "9C", "9D"): "bomb",
        ("BJ", "RJ"): "rocket",
    }
    for cards, expected in cases.items():
        assert classify_cards(cards).kind == expected


@pytest.mark.parametrize(
    "cards",
    [
        ("10S", "JS", "QS", "KS", "AS", "2S"),
        ("AS", "AH", "2S", "2H", "KS", "KH"),
        ("3S", "3H", "3C", "4S", "4H", "4C", "7D"),
    ],
)
def test_rejects_invalid_patterns(cards):
    with pytest.raises(InvalidAction):
        classify_cards(cards)


def test_comparison_respects_shape_and_bomb_hierarchy():
    low = classify_cards(("3S", "4S", "5S", "6S", "7S"))
    high = classify_cards(("4S", "5S", "6S", "7S", "8S"))
    assert compare_plays(high, low)
    assert not compare_plays(classify_cards(("9S",)), classify_cards(("8S", "8H")))
    assert compare_plays(classify_cards(("3S", "3H", "3C", "3D")), high)
    assert compare_plays(classify_cards(("BJ", "RJ")), classify_cards(("AS", "AH", "AC", "AD")))

