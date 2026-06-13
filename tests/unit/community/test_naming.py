"""Unit tests for src/community/naming.py"""

from unittest.mock import patch

from src.community.naming import ANIMALS, generate_fake_name


class TestGenerateFakeName:
    def test_returns_animal_and_number_format(self):
        name = generate_fake_name(set())
        animal, number = name.rsplit(" ", 1)
        assert animal in ANIMALS
        assert number.isdigit()
        assert 10 <= int(number) <= 99

    def test_retries_until_an_unused_name_is_found(self):
        existing = {"נשר 10"}
        with patch("src.community.naming.random.choice", side_effect=["נשר", "דולפין"]), \
                patch("src.community.naming.random.randint", side_effect=[10, 20]):
            result = generate_fake_name(existing)
        assert result == "דולפין 20"

    def test_empty_existing_returns_valid_name(self):
        name = generate_fake_name(set())
        assert isinstance(name, str)
        assert len(name.split(" ")) == 2

    def test_fully_exhausted_still_returns_a_name(self):
        all_names = {f"{a} {n}" for a in ANIMALS for n in range(10, 100)}
        name = generate_fake_name(all_names)
        assert isinstance(name, str)
        assert len(name.split(" ")) == 2
