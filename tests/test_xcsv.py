import os
import io
import tempfile
import hashlib

import pytest
import pandas as pd

import xcsv

base = os.path.dirname(__file__)

def test_version():
    assert xcsv.__version__ == '0.6.0'

@pytest.fixture
def dummy_metadata():
    metadata = {
        'header': {
            'id': '1',
            'title': 'The title',
            'summary': ['This dataset...','The second summary paragraph.','The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain'],
            'authors': 'A B, C D',
            'institution': 'BAS (British Antarctic Survey).',
            'latitude': {'value': '-73.86', 'units': 'degree_north'},
            'longitude': {'value': '-65.46', 'units': 'degree_east'},
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

@pytest.fixture
def short_test_data():
    in_file = base + '/data/short-test-data.csv'

    with xcsv.File(in_file) as f:
        content = f.read()

    return content

@pytest.fixture
def short_missing_value_test_data():
    in_file = base + '/data/short-missing-value-test-data.csv'

    with xcsv.File(in_file) as f:
        content = f.read()

    return content

@pytest.fixture
def short_mislabelled_notes_test_data():
    in_file = base + '/data/short-mislabelled-notes-test-data.csv'

    with xcsv.File(in_file) as f:
        content = f.read()

    return content

@pytest.mark.parametrize(['s','pattern','expected'], [
('a_name (some_units)', r'(?P<name>.+)\s+\((?P<units>.+)\)', {'name': 'a_name', 'units': 'some_units'}),
('a free text string without any units', r'(?P<name>.+)\s+\((?P<units>.+)\)', None),
('  (some_units)', r'(?P<name>.+)\s+\((?P<units>.+)\)', {'name': ' ', 'units': 'some_units'}),
])
def test_parse_tokens(s, pattern, expected):
    actual = xcsv._parse_tokens(s, pattern)
    assert actual == expected

@pytest.mark.parametrize(['s','pattern','expected'], [
('a_name (some_units)', r'(?P<name>.+)\s+\((?P<units>.+)\)', {'name': 'a_name', 'units': 'some_units'}),
('a free text string without any units', r'(?P<name>.+)\s+\((?P<units>.+)\)', None),
('  (some_units)', r'(?P<name>.+)\s+\((?P<units>.+)\)', {'name': '', 'units': 'some_units'}),
])
def test_strip_tokens(s, pattern, expected):
    actual = xcsv._strip_tokens(xcsv._parse_tokens(s, pattern))
    assert actual == expected

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
    expected = {'name': '', 'units': None, 'notes': None}
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
    expected = {'name': '', 'units': 'some_units', 'notes': 'a_note'}
    actual = xcsv.XCSV.parse_column_header_tokens(s)
    assert actual == expected

@pytest.mark.parametrize(['cols','parse_metadata','expected'], [
(pd.Index(['time (year)', 'depth (m)'], dtype='object'), True, {'time (year)': {'name': 'time', 'units': 'year', 'notes': None}, 'depth (m)': {'name': 'depth', 'units': 'm', 'notes': None}}),
(['time (year)', 'depth (m)'], True, {'time (year)': {'name': 'time', 'units': 'year', 'notes': None}, 'depth (m)': {'name': 'depth', 'units': 'm', 'notes': None}}),
(pd.Index(['time (year) [a]', 'depth (m)'], dtype='object'), True, {'time (year) [a]': {'name': 'time', 'units': 'year', 'notes': 'a'}, 'depth (m)': {'name': 'depth', 'units': 'm', 'notes': None}}),
# The (unexpected) token will mess up the units parsing
(pd.Index(['time (year) [a] (unexpected)', 'depth (m)'], dtype='object'), True, {'time (year) [a] (unexpected)': {'name': 'time', 'units': 'year) [a] (unexpected', 'notes': None}, 'depth (m)': {'name': 'depth', 'units': 'm', 'notes': None}}),
(pd.Index(['time (year)', 'depth (m)'], dtype='object'), False, {'time (year)': {'name': 'time (year)'}, 'depth (m)': {'name': 'depth (m)'}}),
])
def test_parse_column_headers(cols, parse_metadata, expected):
    actual = xcsv.XCSV.parse_column_headers(cols, parse_metadata=parse_metadata)
    assert expected == actual

@pytest.mark.parametrize(['parse_metadata','expected'], [
(True, {'time (year) [a]': {'name': 'time', 'units': 'year', 'notes': 'a'}, 'depth (m)': {'name': 'depth', 'units': 'm', 'notes': None}}),
(False, {'time (year) [a]': {'name': 'time (year) [a]'}, 'depth (m)': {'name': 'depth (m)'}}),
])
def test_store_column_headers(dummy_XCSV, parse_metadata, expected):
    f = dummy_XCSV
    actual = f.store_column_headers(parse_metadata=parse_metadata)
    assert expected == f.metadata['column_headers']
    assert expected == actual

@pytest.mark.parametrize(['l','expected'], [
(['line 1', {'value': 'line 2', 'units': 'non units'}], 'line 2 (non units)'),
(['line 1', 'line 2'], ''),
])
def test_get_list_header_exception_context(l, expected):
    actual = xcsv.XCSV._get_list_header_exception_context(l)
    assert expected in actual

def test_reconstruct_file_header_string():
    d = {'value': 'a_value', 'units': 'some_units'}
    expected = 'a_value (some_units)'
    actual = xcsv.XCSV.reconstruct_file_header_string(d)
    assert actual == expected

def test_reconstruct_file_header_string_value_only():
    d = {'value': 'a_value', 'units': None}
    expected = 'a_value'
    actual = xcsv.XCSV.reconstruct_file_header_string(d)
    assert actual == expected

def test_reconstruct_column_header_string():
    d = {'name': 'a_name', 'units': 'some_units', 'notes': 'a_note'}
    expected = 'a_name (some_units) [a_note]'
    actual = xcsv.XCSV.reconstruct_column_header_string(d)
    assert actual == expected

def test_reconstruct_column_header_string_name_and_units_only():
    d = {'name': 'a_name', 'units': 'some_units', 'notes': None}
    expected = 'a_name (some_units)'
    actual = xcsv.XCSV.reconstruct_column_header_string(d)
    assert actual == expected

def test_reconstruct_column_header_string_name_and_notes_only():
    d = {'name': 'a_name', 'units': None, 'notes': 'a_note'}
    expected = 'a_name [a_note]'
    actual = xcsv.XCSV.reconstruct_column_header_string(d)
    assert actual == expected

def test_reconstruct_column_header_string_name_only():
    d = {'name': 'a_name', 'units': None, 'notes': None}
    expected = 'a_name'
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

@pytest.mark.parametrize(['key','expected'], [
('id', '1'),
('summary', ['This dataset...','The second summary paragraph.','The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain']),
('latitude', {'value': '-73.86', 'units': 'degree_north'}),
('non-existent', None)
])
def test_get_metadata_item(short_test_data, key, expected):
    actual = short_test_data.get_metadata_item(key)
    assert actual == expected

@pytest.mark.parametrize(['key','expected', 'section'], [
('depth (m)', {'name': 'depth', 'units': 'm', 'notes': None}, 'column_headers')
])
def test_get_metadata_item_different_section(short_test_data, key, expected, section):
    actual = short_test_data.get_metadata_item(key, section=section)
    assert actual == expected

def test_get_metadata_item_non_existent_section(short_test_data):
    key = 'id'
    section = 'non-existent'

    with pytest.raises(KeyError):
        actual = short_test_data.get_metadata_item(key, section=section)

@pytest.mark.parametrize(['key','default'], [
('non-existent', ''),
('non-existent', 0),
('non-existent', 0.0),
('non-existent', []),
('non-existent', {})
])
def test_get_metadata_item_with_default(short_test_data, key, default):
    actual = short_test_data.get_metadata_item(key, default=default)
    assert actual == default

@pytest.mark.parametrize(['key','expected'], [
('id', '1'),
('summary', 'This dataset...\nThe second summary paragraph.\nThe third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain'),
('latitude', '-73.86 (degree_north)'),
('non-existent', None)
])
def test_get_metadata_item_string(short_test_data, key, expected):
    actual = short_test_data.get_metadata_item_string(key)
    assert actual == expected

@pytest.mark.parametrize(['key','expected', 'section'], [
('depth (m)', 'depth (m)', 'column_headers'),
('time (year) [a]', 'time (year) [a]', 'column_headers')
])
def test_get_metadata_item_string_different_section(short_test_data, key, expected, section):
    actual = short_test_data.get_metadata_item_string(key, section=section)
    assert actual == expected

def test_get_metadata_item_string_non_existent_section(short_test_data):
    key = 'id'
    section = 'non-existent'

    with pytest.raises(KeyError):
        actual = short_test_data.get_metadata_item(key, section=section)

@pytest.mark.parametrize(['key','default'], [
('non-existent', ''),
('non-existent', 0),
('non-existent', 0.0),
('non-existent', []),
('non-existent', {})
])
def test_get_metadata_item_string_with_default(short_test_data, key, default):
    actual = short_test_data.get_metadata_item_value(key, default=default)
    assert actual == default

@pytest.mark.parametrize(['key','expected'], [
('id', '1'),
('summary', 'This dataset...\nThe second summary paragraph.\nThe third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain'),
('latitude', '-73.86'),
('non-existent', None)
])
def test_get_metadata_item_value(short_test_data, key, expected):
    actual = short_test_data.get_metadata_item_value(key)
    assert actual == expected

@pytest.mark.parametrize(['key','expected', 'section'], [
('depth (m)', 'depth', 'column_headers'),
('time (year) [a]', 'time', 'column_headers')
])
def test_get_metadata_item_value_different_section(short_test_data, key, expected, section):
    actual = short_test_data.get_metadata_item_value(key, section=section)
    assert actual == expected

def test_get_metadata_item_value_non_existent_section(short_test_data):
    key = 'id'
    section = 'non-existent'

    with pytest.raises(KeyError):
        actual = short_test_data.get_metadata_item(key, section=section)

@pytest.mark.parametrize(['key','default'], [
('non-existent', ''),
('non-existent', 0),
('non-existent', 0.0),
('non-existent', []),
('non-existent', {})
])
def test_get_metadata_item_value_with_default(short_test_data, key, default):
    actual = short_test_data.get_metadata_item_value(key, default=default)
    assert actual == default

@pytest.mark.parametrize(['key','expected'], [
('id', 1),
('title', 'The title'),
('summary', 'This dataset...\nThe second summary paragraph.\nThe third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain'),
('authors', 'A B, C D'),
('latitude', -73.86),
('longitude', -65.46),
('elevation', 1897),
('[a]', '2012 not a complete year'),
('non-existent', None)
])
def test_get_metadata_item_value_with_cast(short_test_data, key, expected):
    actual = short_test_data.get_metadata_item_value(key, cast=True)
    assert actual == expected

@pytest.mark.parametrize(['key','expected'], [
('time (year) [a]', '2012 not a complete year'),
('depth (m)', None),
('qc [b]', None),
# Now matches header note key, but no column header exists with this key
('qc [mislabelled_b]', None),
('event_marker', None),
('non-existent', None)
])
def test_get_notes_for_column_header(short_mislabelled_notes_test_data, key, expected):
    actual = short_mislabelled_notes_test_data.get_notes_for_column_header(key)
    assert actual == expected

def test_read_short_test_data(dummy_XCSV, short_test_data):
    assert short_test_data.metadata == dummy_XCSV.metadata
    assert short_test_data.data.all().all() == dummy_XCSV.data.all().all()

def test_read_header():
    s = """# id: 1
# title: The title
# summary: This dataset...
"""
    fp = io.StringIO(s)
    f = xcsv.Reader(fp=fp)
    expected = {'id': '1', 'title': 'The title', 'summary': 'This dataset...'}
    header = f.read_header()
    assert header == expected

def test_read_header_no_init_key():
    s = """# This dataset...
"""
    fp = io.StringIO(s)
    f = xcsv.Reader(fp=fp)

    with pytest.raises(ValueError):
        header = f.read_header()

def test_read_header_continuation_simple_form():
    s = """# id: 1
# title: The title
# summary: This dataset...
# The second summary paragraph.
"""
    fp = io.StringIO(s)
    f = xcsv.Reader(fp=fp)
    expected = {'id': '1', 'title': 'The title', 'summary': ['This dataset...','The second summary paragraph.']}
    header = f.read_header()
    assert header == expected

def test_read_header_continuation_escaped_form():
    s = """# id: 1
# title: The title
# summary: This dataset...
# The second summary paragraph.
# : The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain
"""
    fp = io.StringIO(s)
    f = xcsv.Reader(fp=fp)
    expected = {'id': '1', 'title': 'The title', 'summary': ['This dataset...','The second summary paragraph.','The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain']}
    header = f.read_header()
    assert header == expected

def test_read_header_continuation_without_escaped_form():
    # If we forget to escape a continuation line that contains the delimiter
    # in its value, then we end up with an unintended key that is all of the
    # text to the left of the delimiter, with the value being the remainder
    # of the line
    s = """# id: 1
# title: The title
# summary: This dataset...
# The second summary paragraph.
# The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain
"""
    fp = io.StringIO(s)
    f = xcsv.Reader(fp=fp)
    expected = {'id': '1', 'title': 'The title', 'summary': ['This dataset...','The second summary paragraph.'],'The third summary paragraph.  Escaped because it contains the delimiter in a URL https': '//dummy.domain'}
    header = f.read_header()
    assert header == expected

def test_read_header_continuation_repeated_key_form():
    # The repeated key form is identical to the escaped form.  It's
    # essentially just a more verbose expression.  The important bit is that
    # the line includes the delimiter at the start.  If the key was omitted,
    # it would use the previous key anyway, which is the same
    s = """# id: 1
# title: The title
# summary: This dataset...
# The second summary paragraph.
# summary: The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain
"""
    fp = io.StringIO(s)
    f = xcsv.Reader(fp=fp)
    expected = {'id': '1', 'title': 'The title', 'summary': ['This dataset...','The second summary paragraph.','The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain']}
    header = f.read_header()
    assert header == expected

def test_read_header_no_value():
    s = """# id:
"""
    expected = {'id': ''}
    fp = io.StringIO(s)
    f = xcsv.Reader(fp=fp)
    header = f.read_header()
    assert header == expected

def test_set_header_key_value():
    f = xcsv.Reader()
    key, value = 'summary', 'This dataset...'
    f.set_header_key_value(key, value)
    assert f.header[key] == value

    # Check that reading a continutation line converts the existing header
    # item to a list
    key, value = 'summary', 'The second summary paragraph.'
    f.set_header_key_value(key, value)
    assert f.header[key] == ['This dataset...','The second summary paragraph.']

@pytest.mark.parametrize(['missing_value','expected'], [
('999', 999),
('-999', -999),
('-999.0', -999),       # These are probably not what a user intends, but
('0.0', 0),             # are what the function will return
('999.99', 999.99),
('-999.99', -999.99),
('NA', 'NA'),
# missing_value should be a dimensionless, scalar, numeric value
({'value': '-999.99', 'units': 'invalid'}, {'value': '-999.99', 'units': 'invalid'}),
(['-999.99', '-999.99'], ['-999.99', '-999.99'])
])
def test__get_type_cast_missing_value(missing_value, expected):
    f = xcsv.Reader()
    key, value = xcsv.XCSV.DEFAULTS['missing_value_key'], missing_value
    f.set_header_key_value(key, value)
    actual = f._get_type_cast_missing_value()
    assert actual == expected

# Note ['NA','NaN',None] will always be converted to pd.NA by pandas itself
@pytest.mark.parametrize(['missing_value','expected'], [
('999',
pd.DataFrame({
    'time (year) [a]': [2012,2011,2010,2009,2008,2007,2006,2005,2004],
    'depth (m)': [0.575,1.125,2.225,-999,None,-999.99,999.99,None,None]
})),
('-999',
pd.DataFrame({
    'time (year) [a]': [2012,2011,2010,2009,2008,2007,2006,2005,2004],
    'depth (m)': [0.575,1.125,2.225,None,999,-999.99,999.99,None,None]
})),
# Again, this is probably not what a user intends, but will be converted
# because of casting
('-999.0',
pd.DataFrame({
    'time (year) [a]': [2012,2011,2010,2009,2008,2007,2006,2005,2004],
    'depth (m)': [0.575,1.125,2.225,None,999,-999.99,999.99,None,None]
})),
('0.0',
pd.DataFrame({
    'time (year) [a]': [2012,2011,2010,2009,2008,2007,2006,2005,2004],
    'depth (m)': [0.575,1.125,2.225,-999,999,-999.99,999.99,None,None]
})),
('999.99',
pd.DataFrame({
    'time (year) [a]': [2012,2011,2010,2009,2008,2007,2006,2005,2004],
    'depth (m)': [0.575,1.125,2.225,-999,999,-999.99,None,None,None]
})),
('-999.99',
pd.DataFrame({
    'time (year) [a]': [2012,2011,2010,2009,2008,2007,2006,2005,2004],
    'depth (m)': [0.575,1.125,2.225,-999,999,None,999.99,None,None]
})),
('NA',
pd.DataFrame({
    'time (year) [a]': [2012,2011,2010,2009,2008,2007,2006,2005,2004],
    'depth (m)': [0.575,1.125,2.225,-999,999,-999.99,999.99,None,None]
})),
])
def test_mask_missing_values(short_missing_value_test_data, missing_value, expected):
    f = xcsv.Reader()
    f.xcsv = short_missing_value_test_data
    f.data = short_missing_value_test_data.data
    f.header = short_missing_value_test_data.metadata['header']
    f.column_headers = short_missing_value_test_data.metadata['column_headers']
    key, value = xcsv.XCSV.DEFAULTS['missing_value_key'], missing_value
    f.header[key] = value
    f.mask_missing_values()
    pd.testing.assert_frame_equal(f.data, expected, check_dtype=False)

@pytest.mark.parametrize(['missing_value','label', 'idx'], [
('-999.99', 'depth (m)', 5),
('-999', 'depth (m)', 3),
('999.99', 'depth (m)', 6),
('999', 'depth (m)', 4),
('NA', 'depth (m)', 7),
('NaN', 'depth (m)', 8),
])
def test_masked_missing_value_isna(short_missing_value_test_data, missing_value, label, idx):
    f = xcsv.Reader()
    f.xcsv = short_missing_value_test_data
    f.data = short_missing_value_test_data.data
    f.header = short_missing_value_test_data.metadata['header']
    f.column_headers = short_missing_value_test_data.metadata['column_headers']
    key, value = xcsv.XCSV.DEFAULTS['missing_value_key'], missing_value
    f.header[key] = value
    f.mask_missing_values()
    assert pd.isna(f.data[label][idx]) == True

def test_reconstruct_header_lines_list_item():
    f = xcsv.Writer()
    f.header = {'summary': ['This dataset...','The second summary paragraph.']}
    expected = """# summary: This dataset...
# The second summary paragraph.
"""
    actual = '\n'.join(f.reconstruct_header_lines('# ', ': ')) + '\n'
    assert actual == expected

def test_reconstruct_header_lines_escaped_list_item():
    f = xcsv.Writer()
    f.header = {'summary': ['This dataset...','The second summary paragraph.','The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain']}
    expected = """# summary: This dataset...
# The second summary paragraph.
# : The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain
"""
    actual = '\n'.join(f.reconstruct_header_lines('# ', ': ')) + '\n'
    assert actual == expected

def test_reconstruct_header_lines_escaped_list_item_custom_delimiter():
    # Ensure that if a custom delimiter is specified, then any string that
    # contains this is escaped using this leading custom delimiter
    f = xcsv.Writer()
    f.header = {'summary': ['This dataset...','The second summary paragraph.','The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain']}
    expected = """# summary/ This dataset...
# The second summary paragraph.
# / The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain
"""
    actual = '\n'.join(f.reconstruct_header_lines('# ', '/ ')) + '\n'
    assert actual == expected

@pytest.mark.parametrize(['path','opts','expected'], [
('/data/encoded_ascii.csv', {'encoding': 'ASCII'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_ascii.csv', {'encoding': 'UTF-8'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_iso-8859-15.csv', {'encoding': 'ISO-8859-15'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8.csv', {'encoding': 'UTF-8'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_bom.csv', {'encoding': 'UTF-8'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_bom.csv', {'encoding': 'UTF-8-SIG'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_header_and_data_bom.csv', {'encoding': 'UTF-8'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_header_and_data_bom.csv', {'encoding': 'UTF-8-SIG'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_ascii.csv', {}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8.csv', {}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_bom.csv', {}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_header_and_data_bom.csv', {}, {'id': '123', 'title': 'The title'}),
])
def test_read_header_handling_bom(path, opts, expected):
    in_file = base + path

    with open(in_file, **opts) as fp:
        f = xcsv.Reader(fp=fp)
        header = f.read_header()
        assert header == expected

@pytest.mark.parametrize(['path','opts','expected'], [
('/data/encoded_ascii.csv', {'encoding': 'ASCII'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_ascii.csv', {'encoding': 'UTF-8'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_iso-8859-15.csv', {'encoding': 'ISO-8859-15'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8.csv', {'encoding': 'UTF-8'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_bom.csv', {'encoding': 'UTF-8'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_bom.csv', {'encoding': 'UTF-8-SIG'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_header_and_data_bom.csv', {'encoding': 'UTF-8'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_header_and_data_bom.csv', {'encoding': 'UTF-8-SIG'}, {'id': '123', 'title': 'The title'}),
('/data/encoded_ascii.csv', {}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8.csv', {}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_bom.csv', {}, {'id': '123', 'title': 'The title'}),
('/data/encoded_utf-8_header_and_data_bom.csv', {}, {'id': '123', 'title': 'The title'}),
])
def test_read_handling_bom(path, opts, expected):
    in_file = base + path

    with xcsv.File(in_file, **opts) as f:
        content = f.read()
        assert content.metadata['header'] == expected

def get_file_hash(file):
    fhash = None

    with open(file, 'rb') as fp:
        fhash = hashlib.sha1(fp.read()).hexdigest()

    return fhash

def reader_read_csv_with_opts(in_file, header_opts, data_opts):
    content = None

    with open(in_file, mode='r') as fp:
        reader = xcsv.Reader(fp=fp)

        if header_opts and data_opts:
            content = reader.read(header_kwargs=header_opts, data_kwargs=data_opts)
        elif header_opts:
            content = reader.read(header_kwargs=header_opts)
        elif data_opts:
            content = reader.read(data_kwargs=data_opts)
        else:
            content = reader.read()

    return content

def reader_read_json_with_opts(in_file, data_opts):
    content = None

    with open(in_file, mode='r') as fp:
        reader = xcsv.Reader(fp=fp)

        if data_opts:
            content = reader.read_as_json(data_kwargs=data_opts)
        else:
            content = reader.read_as_json()

    return content

def reader_read_with_opts(in_file, header_opts={}, data_opts={}):
    content = None

    if in_file.endswith('.csv'):
        content = reader_read_csv_with_opts(in_file, header_opts, data_opts)
    else:
        content = reader_read_json_with_opts(in_file, data_opts)

    return content

def writer_write_csv_with_opts(out_file, content, header_opts, data_opts):
    with open(out_file, mode='w') as fp:
        writer = xcsv.Writer(fp=fp, xcsv=content)

        if header_opts and data_opts:
            writer.write(header_kwargs=header_opts, data_kwargs=data_opts)
        elif header_opts:
            writer.write(header_kwargs=header_opts)
        elif data_opts:
            writer.write(data_kwargs=data_opts)
        else:
            writer.write()

def writer_write_json_with_opts(out_file, content, data_opts):
    with open(out_file, mode='w') as fp:
        writer = xcsv.Writer(fp=fp, xcsv=content)

        if data_opts:
            writer.write_as_json(data_kwargs=data_opts)
        else:
            writer.write_as_json()

def writer_write_with_opts(out_file, content, header_opts={}, data_opts={}):
    if out_file.endswith('.csv'):
        writer_write_csv_with_opts(out_file, content, header_opts, data_opts)
    else:
        writer_write_json_with_opts(out_file, content, data_opts)

def convert(in_file, out_file, rh_opts={}, rd_opts={}, wh_opts={}, wd_opts={}):
    content = reader_read_with_opts(in_file, header_opts=rh_opts, data_opts=rd_opts)
    writer_write_with_opts(out_file, content, header_opts=wh_opts, data_opts=wd_opts)

@pytest.mark.parametrize('path', [
('/data/short-test-data.csv'),
])
def test_written_matches_read(path):
    in_file = base + path

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = tmp_dir + '/out.csv'

        # Write out the read-in data, as-is.  These should be identical, as
        # long as all values in a column are of the same type.
        # For example, if a column contains floats and integers, the output
        # data will be formatted as floats and so may introduce small
        # differences, e.g. -1 will become -1.0
        content = reader_read_with_opts(in_file)
        writer_write_with_opts(out_file, content)

        # Compare the original and the written out files
        hash1 = get_file_hash(in_file)
        hash2 = get_file_hash(out_file)
        assert hash1 == hash2

@pytest.mark.parametrize(['path','header_opts','data_opts'], [
('/data/short-test-data.csv', {}, {}),
('/data/short-test-data.csv', {'comment': '#'}, {}),
('/data/short-test-data.csv', {}, {'comment': '#'}),
('/data/short-test-data.csv', {'comment': '#'}, {'comment': '#'}),
('/data/short-test-data.csv', {'comment': '#'}, {'comment': '#', 'parse_dates': ['time (year) [a]']}),
])
def test_reader_read_csv_opts(path, header_opts, data_opts):
    in_file = base + path
    reader_read_csv_with_opts(in_file, header_opts, data_opts)

@pytest.mark.parametrize(['path','header_opts','data_opts'], [
('/data/short-test-data.csv', {}, {}),
('/data/short-test-data.csv', {'comment': '# '}, {}),
('/data/short-test-data.csv', {}, {'index': False}),
('/data/short-test-data.csv', {'comment': '# '}, {'index': False}),
('/data/short-test-data.csv', {'comment': '# '}, {'index': True}),
('/data/short-test-data.csv', {'comment': '# '}, {'index': False, 'date_format': '%Y-%m-%dT%H:%M:%S', 'float_format': '%.4g'}),
('/data/short-test-data.csv', {'comment': '# '}, {'index': False, 'date_format': '%Y-%m-%d', 'float_format': '%.6f'}),
])
def test_writer_write_csv_opts(path, header_opts, data_opts):
    in_file = base + path

    with xcsv.File(in_file) as f:
        content = f.read()

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = tmp_dir + '/out.csv'
        writer_write_csv_with_opts(out_file, content, header_opts, data_opts)

@pytest.mark.parametrize(['path','data_opts'], [
('/data/short-test-data.json', {}),
])
def test_reader_read_json_opts(path, data_opts):
    in_file = base + path
    reader_read_json_with_opts(in_file, data_opts)

@pytest.mark.parametrize(['path','data_opts'], [
('/data/short-test-data.csv', {}),
])
def test_writer_write_json_opts(path, data_opts):
    in_file = base + path

    with xcsv.File(in_file) as f:
        content = f.read()

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = tmp_dir + '/out.json'
        writer_write_json_with_opts(out_file, content, data_opts)

@pytest.mark.parametrize(['path','data_opts','compare'], [
('/data/short-test-data.csv', {}, 'metadata'),
('/data/short-test-data.csv', {'index': False, 'float_format': '%.4g'}, 'metadata'),
('/data/short-test-data.csv', {'index': False, 'float_format': '%.4g'}, 'data'),
('/data/short-test-data.csv', {'index': False, 'float_format': '%.4g'}, 'hash'),
])
def test_convert_recover_and_compare(path, data_opts, compare):
    in_file = base + path

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = tmp_dir + '/tmp.json'
        out_file = tmp_dir + '/out.csv'

        convert(in_file, tmp_file)
        convert(tmp_file, out_file, wh_opts={}, wd_opts=data_opts)

        # Compare the original and the recovered files
        if compare == 'header' or compare == 'data':
            content1 = reader_read_with_opts(in_file)
            content2 = reader_read_with_opts(out_file)

        if compare == 'header':
            assert content1.metadata == content2.metadata
        elif compare == 'data':
            assert content1.data.all().all() == content2.data.all().all()
        elif compare == 'hash':
            hash1 = get_file_hash(in_file)
            hash2 = get_file_hash(out_file)
            assert hash1 == hash2

