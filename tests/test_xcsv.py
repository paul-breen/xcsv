import os

import pytest
import pandas as pd

import xcsv

base = os.path.dirname(__file__)

def test_version():
    assert xcsv.__version__ == '0.1.0'

@pytest.fixture
def dummy_metadata():
    metadata = {
        'header': {
            'id': '1',
            'title': 'The title',
            'summary': 'This dataset...',
            'authors': 'A B, C D',
            'latitude': {'value': '-73.86', 'units': 'degree_north'},
            'longitude': {'value': '-65.86', 'units': 'degree_east'},
            'elevation': {'value': '1897', 'units': 'm a.s.l.'},
            '[a]': '2012 not a complete year'
        },
        'column_headers': {
            'time (year) [a]': {'name': 'time', 'units': 'year', 'notes': 'a'},
            'depth (m)': {'name': 'depth', 'units': 'm', 'notes': None}
        }
    }

    return metadata

@pytest.fixture
def dummy_data():
    data = pd.DataFrame({
        'time (year) [a]': [2012,2011,2010],
        'depth (m)': [0.575,1.125,2.225]
    })

    return data
 
@pytest.fixture
def dummy_XCSV(dummy_metadata, dummy_data):
    return xcsv.XCSV(metadata=dummy_metadata, data=dummy_data)
 
def test_parse_tokens_dict():
    pattern = r'(?P<name>.+)\s+\((?P<units>.+)\)'
    s = 'a_name (some_units)'
    expected = {'name': 'a_name', 'units': 'some_units'}
    actual = xcsv._parse_tokens(s, pattern)
    assert actual == expected

def test_parse_tokens_None():
    pattern = r'(?P<name>.+)\s+\((?P<units>.+)\)'
    s = 'a free text string without any units'
    actual = xcsv._parse_tokens(s, pattern)
    assert actual is None

def test_parse_file_header_tokens_dict():
    s = 'a_value (some_units)'
    expected = {'value': 'a_value', 'units': 'some_units'}
    actual = xcsv.XCSV.parse_file_header_tokens(s)
    assert actual == expected

def test_parse_file_header_tokens_None():
    s = 'a_value'
    actual = xcsv.XCSV.parse_file_header_tokens(s)
    assert actual is None

def test_parse_file_header_tokens_empty_parens():
    s = 'a_value ()'
    actual = xcsv.XCSV.parse_file_header_tokens(s)
    assert actual is None

def test_parse_column_header_tokens_full_dict():
    s = 'a_name (some_units) [a_note]'
    expected = {'name': 'a_name', 'units': 'some_units', 'notes': 'a_note'}
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual == expected

def test_parse_column_header_tokens_name_only():
    s = 'a_name'
    expected = {'name': 'a_name', 'units': None, 'notes': None}
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual == expected

def test_parse_column_header_tokens_units_only():
    s = '(some_units)'
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual is None

def test_parse_column_header_tokens_notes_only():
    s = '[a_note]'
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual is None

def test_parse_column_header_tokens_name_and_units():
    s = 'a_name (some_units)'
    expected = {'name': 'a_name', 'units': 'some_units', 'notes': None}
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual == expected

def test_parse_column_header_tokens_name_and_notes():
    s = 'a_name [a_note]'
    expected = {'name': 'a_name', 'units': None, 'notes': 'a_note'}
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual == expected

def test_parse_column_header_tokens_units_and_notes():
    s = '(some_units) [a_note]'
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual is None

def test_parse_column_header_tokens_empty():
    s = ''
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual is None

def test_parse_column_header_tokens_space():
    s = ' '
    expected = {'name': ' ', 'units': None, 'notes': None}
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual == expected

def test_parse_column_header_tokens_space_empty_parens():
    s = ' ()'
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual is None

def test_parse_column_header_tokens_space_empty_brackets():
    s = ' []'
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual is None

def test_parse_column_header_tokens_space_empty_parens_empty_brackets():
    s = ' () []'
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual is None

def test_parse_column_header_tokens_space_units_empty_brackets():
    s = ' (some_units) []'
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual is None

def test_parse_column_header_tokens_space_empty_parens_notes():
    s = ' () [a_note]'
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual is None

def test_parse_column_header_tokens_space_units_notes():
    s = ' (some_units) [a_note]'
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual is None

def test_parse_column_header_tokens_spaces_units_notes():
    # At least one space is required as separator between name and units
    s = '  (some_units) [a_note]'
    expected = {'name': ' ', 'units': 'some_units', 'notes': 'a_note'}
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual == expected

def test_reconstruct_file_header_string():
    d = {'value': 'a_value', 'units': 'some_units'}
    expected = 'a_value (some_units)'
    actual = xcsv.XCSV.reconstruct_file_header_string(d)
    assert actual == expected

def test_reconstruct_file_header_string_value_only():
    d = {'value': 'a_value', 'units': None}
    expected = 'a_value (None)'
    actual = xcsv.XCSV.reconstruct_file_header_string(d)
    assert actual == expected

def test_reconstruct_column_header_string():
    d = {'name': 'a_name', 'units': 'some_units', 'notes': 'a_note'}
    expected = 'a_name (some_units) [a_note]'
    actual = xcsv.XCSV.reconstruct_column_header_string(d)
    assert actual == expected

def test_reconstruct_column_header_string_name_only():
    d = {'name': 'a_name', 'units': None, 'notes': None}
    expected = 'a_name (None) [None]'
    actual = xcsv.XCSV.reconstruct_column_header_string(d)
    assert actual == expected

def test_get_column_header_name_map(dummy_XCSV):
    f = dummy_XCSV
    expected = {'time (year) [a]': 'time', 'depth (m)': 'depth'}
    actual = f.get_column_header_name_map()
    assert actual == expected

def test_get_column_header_label_map(dummy_XCSV):
    f = dummy_XCSV
    expected = {'time': 'time (year) [a]', 'depth': 'depth (m)'}
    actual = f.get_column_header_label_map()
    assert actual == expected

def test_get_column_header_name_map_uninitialised():
    f = xcsv.XCSV()

    # The metadata property is initially None, so cannot be subscripted
    with pytest.raises(TypeError):
        actual = f.get_column_header_name_map()

def test_get_column_header_label_map_uninitialised():
    f = xcsv.XCSV()

    with pytest.raises(TypeError):
        actual = f.get_column_header_label_map()

def test_get_column_header_name_map_empty():
    f = xcsv.XCSV(metadata={'column_headers':{}})
    expected = {}
    actual = f.get_column_header_name_map()
    assert actual == expected

def test_get_column_header_label_map_empty():
    f = xcsv.XCSV(metadata={'column_headers':{}})
    expected = {}
    actual = f.get_column_header_label_map()
    assert actual == expected

def test_rename_column_headers_as_names(dummy_XCSV):
    f = dummy_XCSV
    expected = ['time', 'depth']
    f.rename_column_headers_as_names()
    assert f.data.columns.to_list() == expected

def test_rename_column_headers_as_labels(dummy_XCSV):
    f = dummy_XCSV
    expected = ['time (year) [a]', 'depth (m)']
    f.rename_column_headers_as_labels()
    assert f.data.columns.to_list() == expected

def test_rename_column_headers_as_names_uninitialised():
    f = xcsv.XCSV()

    with pytest.raises(TypeError):
        f.rename_column_headers_as_names()

def test_rename_column_headers_as_labels_uninitialised():
    f = xcsv.XCSV()

    with pytest.raises(TypeError):
        f.rename_column_headers_as_labels()

def test_rename_column_headers_as_names_empty(dummy_data):
    f = xcsv.XCSV(metadata={'column_headers':{}}, data=dummy_data)
    expected = ['time (year) [a]', 'depth (m)']
    # If passed an empty dict, pandas doesn't rename the column headers
    f.rename_column_headers_as_names()
    assert f.data.columns.to_list() == expected

def test_rename_column_headers_as_labels_empty(dummy_data):
    f = xcsv.XCSV(metadata={'column_headers':{}}, data=dummy_data)
    expected = ['time (year) [a]', 'depth (m)']
    f.rename_column_headers_as_labels()
    assert f.data.columns.to_list() == expected

