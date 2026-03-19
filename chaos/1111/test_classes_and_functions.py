# ----- Imports ----- #

import sys
import os
from classes_and_functions import (
    UserProfile,
    HealthRecord,
    Location,
    PaginatedResponse,
    DataTable,
)
import unittest

# ----- Other ----- #

sys.path.insert(0, os.path.dirname(__file__))
if __name__ == "__main__":
    unittest.main()

# ----- Classes ----- #

class TestUserProfile(unittest.TestCase):
    def test_init_stores_attributes(self):
        profile = UserProfile(
            user_id=1,
            username="john_doe",
            email="john@example.com",
        )
        self.assertEqual(profile.user_id, 1)
        self.assertEqual(profile.email, "john@example.com")

    def test_username_is_normalized_on_init(self):
        # normalize_username strips, lowercases, and replaces spaces with underscores
        profile = UserProfile(
            user_id=2,
            username="  Jane Doe  ",
            email="jane@example.com",
        )
        self.assertEqual(profile.username, "jane_doe")

    def test_display_name_replaces_underscores_and_titles(self):
        profile = UserProfile(
            user_id=1,
            username="john_doe",
            email="john@example.com",
        )
        self.assertEqual(profile.display_name(), "John Doe")

    def test_display_name_single_word(self):
        profile = UserProfile(
            user_id=3,
            username="alice",
            email="alice@example.com",
        )
        self.assertEqual(profile.display_name(), "Alice")

    def test_display_name_already_titlecase_username(self):
        profile = UserProfile(
            user_id=4,
            username="Bob_Smith",
            email="bob@example.com",
        )
        # normalize_username lowercases first, then display_name titles
        self.assertEqual(profile.display_name(), "Bob Smith")


class TestHealthRecord(unittest.TestCase):
    def setUp(self):
        # 70 kg, 1.75 m → BMI ≈ 22.86 (normal)
        self.normal = HealthRecord(
            patient_id="p1",
            weight=70,
            height=1.75,
            age=30,
            notes="",
        )
        # 50 kg, 1.75 m → BMI ≈ 16.33 (underweight)
        self.underweight = HealthRecord(
            patient_id="p2",
            weight=50,
            height=1.75,
            age=25,
            notes="",
        )
        # 80 kg, 1.65 m → BMI ≈ 29.38 (overweight)
        self.overweight = HealthRecord(
            patient_id="p3",
            weight=80,
            height=1.65,
            age=40,
            notes="",
        )
        # 100 kg, 1.70 m → BMI ≈ 34.60 (obese)
        self.obese = HealthRecord(
            patient_id="p4",
            weight=100,
            height=1.70,
            age=45,
            notes="",
        )

    def test_bmi_calculation(self):
        expected = 70 / (1.75**2)
        self.assertAlmostEqual(
            self.normal.bmi(),
            expected,
            places=5,
        )

    def test_bmi_category_normal(self):
        self.assertEqual(self.normal.bmi_category(), "normal")

    def test_bmi_category_underweight(self):
        self.assertEqual(self.underweight.bmi_category(), "underweight")

    def test_bmi_category_overweight(self):
        self.assertEqual(self.overweight.bmi_category(), "overweight")

    def test_bmi_category_obese(self):
        self.assertEqual(self.obese.bmi_category(), "obese")

    def test_bmi_boundary_underweight_normal(self):
        # BMI exactly 18.5 → normal (not underweight)
        # weight = 18.5 * height^2; use height=1.0 for simplicity
        record = HealthRecord(
            patient_id="b1",
            weight=18.5,
            height=1.0,
            age=20,
            notes="",
        )
        self.assertEqual(record.bmi_category(), "normal")

    def test_bmi_boundary_normal_overweight(self):
        # BMI exactly 25.0 → overweight
        record = HealthRecord(
            patient_id="b2",
            weight=25.0,
            height=1.0,
            age=20,
            notes="",
        )
        self.assertEqual(record.bmi_category(), "overweight")

    def test_bmi_boundary_overweight_obese(self):
        # BMI exactly 30.0 → obese
        record = HealthRecord(
            patient_id="b3",
            weight=30.0,
            height=1.0,
            age=20,
            notes="",
        )
        self.assertEqual(record.bmi_category(), "obese")


class TestLocation(unittest.TestCase):
    def setUp(self):
        self.london = Location(
            name="London",
            latitude=51.5074,
            longitude=-0.1278,
            country_code="GB",
        )
        self.paris = Location(
            name="Paris",
            latitude=48.8566,
            longitude=2.3522,
            country_code="FR",
        )
        self.same = Location(
            name="London Copy",
            latitude=51.5074,
            longitude=-0.1278,
            country_code="GB",
        )

    def test_init_stores_attributes(self):
        self.assertEqual(self.london.name, "London")
        self.assertEqual(self.london.latitude, 51.5074)
        self.assertEqual(self.london.longitude, -0.1278)
        self.assertEqual(self.london.country_code, "GB")

    def test_distance_to_known_cities(self):
        # London to Paris is approximately 340 km
        dist = self.london.distance_to(self.paris)
        self.assertAlmostEqual(
            dist,
            340,
            delta=10,
        )

    def test_distance_to_same_location_is_zero(self):
        dist = self.london.distance_to(self.same)
        self.assertAlmostEqual(
            dist,
            0.0,
            places=5,
        )

    def test_distance_is_symmetric(self):
        d1 = self.london.distance_to(self.paris)
        d2 = self.paris.distance_to(self.london)
        self.assertAlmostEqual(
            d1,
            d2,
            places=5,
        )

    def test_formatted(self):
        self.assertEqual(self.london.formatted(), "London (GB)")
        self.assertEqual(self.paris.formatted(), "Paris (FR)")


class TestPaginatedResponse(unittest.TestCase):
    def _make(
        self,
        total,
        page,
        page_size,
        ):
        items = list(range(min(page_size, total)))
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def test_has_next_true_when_more_pages(self):
        resp = self._make(
            total=30,
            page=1,
            page_size=10,
        )
        self.assertTrue(resp.has_next())

    def test_has_next_false_on_last_page(self):
        resp = self._make(
            total=30,
            page=3,
            page_size=10,
        )
        self.assertFalse(resp.has_next())

    def test_has_next_false_when_total_fits_single_page(self):
        resp = self._make(
            total=5,
            page=1,
            page_size=10,
        )
        self.assertFalse(resp.has_next())

    def test_has_prev_false_on_first_page(self):
        resp = self._make(
            total=30,
            page=1,
            page_size=10,
        )
        self.assertFalse(resp.has_prev())

    def test_has_prev_true_on_second_page(self):
        resp = self._make(
            total=30,
            page=2,
            page_size=10,
        )
        self.assertTrue(resp.has_prev())

    def test_has_prev_true_on_last_page(self):
        resp = self._make(
            total=30,
            page=3,
            page_size=10,
        )
        self.assertTrue(resp.has_prev())

    def test_single_page_no_next_no_prev(self):
        resp = self._make(
            total=3,
            page=1,
            page_size=10,
        )
        self.assertFalse(resp.has_next())
        self.assertFalse(resp.has_prev())


class TestDataTable(unittest.TestCase):
    def setUp(self):
        self.columns = ["name", "age", "city"]
        self.rows = [
            ["Alice", 30, "NYC"],
            ["Bob", 25, "LA"],
            ["Charlie", 30, "NYC"],
            ["Diana", 28, "LA"],
        ]
        self.table = DataTable(
            columns=self.columns,
            rows=self.rows,
            title="People",
        )

    def test_filter_rows_returns_matching_rows(self):
        result = self.table.filter_rows("city", "NYC")
        self.assertEqual(result, [["Alice", 30, "NYC"], ["Charlie", 30, "NYC"]])

    def test_filter_rows_no_match_returns_empty(self):
        result = self.table.filter_rows("city", "Chicago")
        self.assertEqual(result, [])

    def test_filter_rows_by_numeric_value(self):
        result = self.table.filter_rows("age", 30)
        self.assertEqual(result, [["Alice", 30, "NYC"], ["Charlie", 30, "NYC"]])

    def test_filter_rows_single_match(self):
        result = self.table.filter_rows("name", "Bob")
        self.assertEqual(result, [["Bob", 25, "LA"]])

    def test_to_csv_header_row(self):
        csv = self.table.to_csv()
        first_line = csv.splitlines()[0]
        self.assertEqual(first_line, "name,age,city")

    def test_to_csv_data_rows(self):
        csv = self.table.to_csv()
        lines = csv.splitlines()
        self.assertEqual(lines[1], "Alice,30,NYC")
        self.assertEqual(lines[2], "Bob,25,LA")

    def test_to_csv_row_count(self):
        csv = self.table.to_csv()
        lines = csv.splitlines()
        # 1 header + 4 data rows
        self.assertEqual(len(lines), 5)

    def test_to_csv_empty_table(self):
        empty = DataTable(
            columns=["x", "y"],
            rows=[],
            title="Empty",
        )
        csv = empty.to_csv()
        self.assertEqual(csv, "x,y")
