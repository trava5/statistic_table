import pytest

from statistic_table.config import (
    SESTAVY_COLUMNS,
    ZAPASY_COLUMNS,
    ColumnGroup,
    check_capacity,
    col_to_index,
)


@pytest.mark.parametrize(
    ("letter", "index"),
    [("A", 0), ("F", 5), ("I", 8), ("J", 9), ("T", 19), ("U", 20), ("AM", 38), ("AR", 43),
     ("BA", 52), ("BC", 54), ("BN", 65), ("CJ", 87), ("CO", 92), ("CT", 97), ("CW", 100)],
)
def test_col_to_index(letter, index):
    assert col_to_index(letter) == index


@pytest.mark.parametrize(
    ("name", "expected_capacity"),
    [
        ("branky", 11),
        ("prihravky", 19),
        ("vylouceni_jmena", 12),
        ("vylouceni_minuty", 12),
        ("skore_treti", 4),
    ],
)
def test_zapasy_capacities(name, expected_capacity):
    assert ZAPASY_COLUMNS[name].capacity == expected_capacity


@pytest.mark.parametrize(
    ("name", "expected_capacity"),
    [("obranci", 7), ("utocnici", 14)],
)
def test_sestavy_capacities(name, expected_capacity):
    assert SESTAVY_COLUMNS[name].capacity == expected_capacity


def test_check_capacity_passes_within_limit():
    group = ColumnGroup("branky", "J", "T")
    check_capacity(group, ["Novák"] * group.capacity, context="zápas 4002")


def test_check_capacity_raises_on_overflow():
    group = ColumnGroup("branky", "J", "T")
    with pytest.raises(ValueError, match="zápas 4002"):
        check_capacity(group, ["Novák"] * (group.capacity + 1), context="zápas 4002")
