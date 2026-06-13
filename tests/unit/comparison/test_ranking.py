"""Unit tests for src/comparison/ranking.py"""

from src.comparison.ranking import get_client_ranking
from tests.conftest import make_fund


class TestGetClientRanking:
    def _sorted_funds(self, ids):
        return [make_fund(fid) for fid in ids]

    def test_finds_rank_at_first_position(self):
        funds = self._sorted_funds(["A", "B", "C"])
        rank, total = get_client_ranking(funds, "A")
        assert rank == 1
        assert total == 3

    def test_finds_rank_at_last_position(self):
        funds = self._sorted_funds(["A", "B", "C"])
        rank, total = get_client_ranking(funds, "C")
        assert rank == 3
        assert total == 3

    def test_not_found_returns_none(self):
        funds = self._sorted_funds(["A", "B"])
        rank, total = get_client_ranking(funds, "Z")
        assert rank is None
        assert total == 2

    def test_empty_list(self):
        rank, total = get_client_ranking([], "X")
        assert rank is None
        assert total == 0

    def test_total_reflects_full_list_length(self):
        funds = self._sorted_funds(["A", "B", "C", "D", "E"])
        _, total = get_client_ranking(funds, "C")
        assert total == 5
