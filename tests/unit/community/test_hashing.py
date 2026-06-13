"""Unit tests for src/community/hashing.py"""

from src.community.hashing import hash_client_id


class TestHashClientId:
    def test_deterministic(self):
        assert hash_client_id("123456789") == hash_client_id("123456789")

    def test_different_ids_give_different_hashes(self):
        assert hash_client_id("111111111") != hash_client_id("222222222")

    def test_returns_64_char_hex_string(self):
        result = hash_client_id("test_id")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_sensitive_to_case(self):
        assert hash_client_id("ABC") != hash_client_id("abc")
