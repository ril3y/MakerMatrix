import pytest
import random
from unittest.mock import patch, Mock

from parsers.boltdepot_parser import BoltDepotParser


@pytest.fixture
def random_part_number():
    # Generate a random integer between 1 and 6000
    return random.randint(1, 6000)


@pytest.fixture
def boltdepot_parser():
    return BoltDepotParser()


def test_matches_real_data(boltdepot_parser, random_part_number):
    sample_byte_data = f"http://boltdepot.com/Product-Details.aspx?product={random_part_number}".encode('utf-8')
    assert boltdepot_parser.matches(sample_byte_data) == True


def test_parse_real_data(boltdepot_parser, random_part_number):
    sample_byte_data = f"http://boltdepot.com/Product-Details.aspx?product={random_part_number}".encode('utf-8')
    boltdepot_parser.parse(sample_byte_data)
    assert boltdepot_parser.part.part_number == str(random_part_number)


# def test_enrich_real_data(boltdepot_parser, random_part_number):
#     sample_byte_data = f"http://boltdepot.com/Product-Details.aspx?product={random_part_number}".encode('utf-8')
#     boltdepot_parser.parse(sample_byte_data)
#     result = boltdepot_parser.enrich()
#
#     assert result is not None
#     # Additional assertions can be added here


def test_parse_real_data(boltdepot_parser):
    sample_byte_data = f"https://boltdepot.com/Product-Details.aspx?product=4123".encode('utf-8')
    boltdepot_parser.parse(sample_byte_data)
    boltdepot_parser.enrich()
    part_dict = boltdepot_parser.to_dict()

    # Additional assertions for other fields
    assert part_dict['additional_properties']['height'] == "1/4"
    assert part_dict['additional_properties']['thread count'] == '14'


