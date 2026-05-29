"""Unit tests for src/parsers/xml_utils.py"""

import xml.etree.ElementTree as ET

import pytest

from src.parsers.xml_utils import extract_data_from_xml


def _el(xml_str: str) -> ET.Element:
    return ET.fromstring(xml_str)


class TestExtractDataFromXml:
    def test_returns_string_text_by_default(self):
        row = _el("<Row><Name>Alice</Name></Row>")
        assert extract_data_from_xml("Name", row) == "Alice"

    def test_returns_na_when_element_missing(self):
        row = _el("<Row></Row>")
        assert extract_data_from_xml("Missing", row) == "N/A"

    def test_returns_zero_float_when_element_missing_numeric(self):
        row = _el("<Row></Row>")
        assert extract_data_from_xml("Missing", row, float) == 0.0

    def test_returns_zero_int_when_element_missing_numeric(self):
        row = _el("<Row></Row>")
        assert extract_data_from_xml("Missing", row, int) == 0.0

    def test_returns_na_when_element_has_no_text(self):
        row = _el("<Row><Empty/></Row>")
        assert extract_data_from_xml("Empty", row) == "N/A"

    def test_returns_zero_float_when_element_has_no_text(self):
        row = _el("<Row><Empty/></Row>")
        assert extract_data_from_xml("Empty", row, float) == 0.0

    def test_casts_to_float(self):
        row = _el("<Row><Val>3.14</Val></Row>")
        result = extract_data_from_xml("Val", row, float)
        assert isinstance(result, float)
        assert abs(result - 3.14) < 1e-9

    def test_casts_to_int(self):
        row = _el("<Row><Val>42</Val></Row>")
        result = extract_data_from_xml("Val", row, int)
        assert result == 42
        assert isinstance(result, int)

    def test_xpath_expression(self):
        row = _el("<Row><Nested><Deep>Hello</Deep></Nested></Row>")
        assert extract_data_from_xml(".//Deep", row) == "Hello"

    def test_nested_xpath_missing(self):
        row = _el("<Row><Nested></Nested></Row>")
        assert extract_data_from_xml(".//Deep", row) == "N/A"

    def test_negative_float(self):
        row = _el("<Row><Val>-5.5</Val></Row>")
        assert extract_data_from_xml("Val", row, float) == -5.5

    def test_whitespace_in_text(self):
        row = _el("<Row><Name>  spaces  </Name></Row>")
        result = extract_data_from_xml("Name", row)
        assert result == "  spaces  "

    def test_zero_string_text_not_treated_as_missing(self):
        row = _el("<Row><Val>0</Val></Row>")
        assert extract_data_from_xml("Val", row) == "0"

    def test_zero_float_text_returns_zero(self):
        row = _el("<Row><Val>0.0</Val></Row>")
        assert extract_data_from_xml("Val", row, float) == 0.0
