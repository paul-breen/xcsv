import os
import io

import pytest
import pandas as pd

import xcsv

base = os.path.dirname(__file__)

def test_version():
    assert xcsv.__version__ == '0.5.0'

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

