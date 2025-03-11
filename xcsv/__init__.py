###############################################################################
# Project: Extended CSV common file format
# Purpose: Classes to encapsulate an extended CSV file
# Author:  Paul M. Breen
# Date:    2022-04-14
###############################################################################

"""
Package for working with extended CSV (XCSV) files

Extended CSV format

* Extended header section of parseable atttributes, introduced by '#'.
* Header row of variable name and units for each column.
* Data rows.
"""

__version__ = '0.6.0'

import re
import argparse
import codecs
import encodings
import json
import io

import pandas as pd

UTF_8_BOM = codecs.BOM_UTF8.decode('utf-8')

def _parse_tokens(s, pattern):
    """
    Parse tokens from the given string

    :param s: The string containing parseable tokens
    :type s: str
    :param pattern: The regular expression to parse tokens from the string
    :type pattern: str
    :returns: The parsed tokens or None if no matches were found
    :rtype: dict or None
    """

    tokens = None
    matches = re.search(pattern, s)

    if matches:
        tokens = matches.groupdict()

    return tokens

def _strip_tokens(tokens):
    """
    Strip the values of a parsed tokens dict

    :param tokens: The parsed tokens
    :type tokens: dict or None
    :returns: The parsed tokens with stripped values or None
    :rtype: dict or None
    """

    if tokens:
        for key in tokens:
            # If the RE pattern failed to match an optional component,
            # e.g. 'notes', then it will be None and so have no strip()
            try:
                tokens[key] = tokens[key].strip()
            except AttributeError:
                pass

    return tokens

def _get_type_cast_value(str_value):
    """
    Cast a string representation of the given value to the most
    appropriate primitive numeric type

    :param str_value: The string representation of the numeric value
    :type str_value: str
    :returns: A suitably cast primitive type of the value or the string as-is
    :rtype: One of [int, float, str]
    """

    for func in [int, float]:
        try:
            cast_value = func(str_value)
            return cast_value
        except (ValueError, TypeError):
            continue

    return str_value

class XCSV(object):
    """
    Class for an extended CSV object
    """

    DEFAULTS = {
        'file_header_keys': ['value', 'units'],
        'file_header_default_key': 'value',
        'file_header_pattern': r'(?P<value>.+)\s+\((?P<units>.+)\)$',
        'file_header_templates': ['{value}', '({units})'],
        'column_header_keys': ['name', 'units', 'notes'],
        'column_header_default_key': 'name',
        'column_header_pattern': r'(?P<name>[^][)(]+)(\s+\((?P<units>.+)\))?(\s+\[(?P<notes>.+)\])?$',
        'column_header_templates': ['{name}', '({units})', '[{notes}]'],
        'missing_value_key': 'missing_value'
    }

    def __init__(self, metadata=None, data=None):
        """
        Constructor

        :param metadata: The extended CSV metadata
        :type metadata: dict
        :param data: The extended CSV data
        :type data: pandas.dataframe
        """

        self.metadata = metadata
        self.data = data

    def __repr__(self):
        return f'{self.__class__!s}({self.__dict__!r})'

    def __str__(self):
        return f'{self.__dict__!r}'

    @classmethod
    def parse_file_header_tokens(cls, s):
        """
        Parse value and units from the given file header value string
        See `cls.DEFAULTS['file_header_pattern']` and `_parse_tokens()`
        """

        pattern = cls.DEFAULTS['file_header_pattern']

        return _strip_tokens(_parse_tokens(s, pattern))

    @classmethod
    def parse_column_header_tokens(cls, s):
        """
        Parse name, units and notes from the given column header string
        See `cls.DEFAULTS['column_header_pattern']` and `_parse_tokens()`
        """

        pattern = cls.DEFAULTS['column_header_pattern']

        return _strip_tokens(_parse_tokens(s, pattern))

    @classmethod
    def parse_column_headers(cls, cols, parse_metadata=True):
        """
        Parse each of the given column header strings from the cols list
        See `parse_column_header_tokens()`
        """

        column_headers = {}
        def_key = cls.DEFAULTS['column_header_default_key']

        for col in cols:
            if parse_metadata:
                tokens = cls.parse_column_header_tokens(col)

                try:
                    column_headers[col] = tokens
                except KeyError:
                    pass
            else:
                column_headers[col] = {def_key: col}

        return column_headers

    @classmethod
    def _get_list_header_exception_context(cls, l):
        """
        Get some context for an exception message where a list header item
        contains a dict
        """

        note = ''
        candidates = [i for i in l if isinstance(i, dict)]

        if candidates:
            note = f"XCSV has parsed an element in a list header item as a value/units dict. This is unsupported in list header items. If this wasn't intended to be a value/units dict, then ensure that the line doesn't end with a closing parenthesis ')', either by removing the parentheses or adding some text after the closing parenthesis. A '.' would suffice."
            d = candidates[0]
            line = cls.reconstruct_file_header_string(d)
            note += f"\nThe cause is this line: {line}\nwhich has been parsed as: {d}"

        return note

    @classmethod
    def recombine_list_header_string(cls, l, sep='\n'):
        """
        Recombine the header value string from the given list
        """

        try:
            s = sep.join(l)
        except TypeError as e:
            note = cls._get_list_header_exception_context(l)
            raise TypeError(note) from e

        return s

    @classmethod
    def _reconstruct_header_string(cls, d, keys, templates, sep=' '):
        """
        Reconstruct the header value string from the given dict

        If a member of the header dict is None, then it is not included
        in the output value string.  This allows reconstructing the header
        as it would have appeared in the original file.
        """

        template_components = []

        for key, tmpl in zip(keys, templates):
            if key in d and d[key] is not None:
                template_components.append(tmpl)

        template = sep.join(template_components)

        return template.format(**d)

    @classmethod
    def reconstruct_file_header_string(cls, d):
        """
        Reconstruct the header value string from the given dict
        See `cls.DEFAULTS['file_header_templates']`
        """

        return cls._reconstruct_header_string(d, cls.DEFAULTS['file_header_keys'], cls.DEFAULTS['file_header_templates'])

    @classmethod
    def reconstruct_column_header_string(cls, d):
        """
        Reconstruct the column header string from the given dict
        See `cls.DEFAULTS['column_header_templates']`
        """

        return cls._reconstruct_header_string(d, cls.DEFAULTS['column_header_keys'], cls.DEFAULTS['column_header_templates'])

    def get_column_header_name_map(self):
        """
        Get a map of column header labels to column header names

        :returns: The column map
        :rtype: dict
        """

        col_map = {}
        def_key = self.DEFAULTS['column_header_default_key']

        for key in self.metadata['column_headers']:
            col_map[key] = self.metadata['column_headers'][key][def_key]

        return col_map

    def get_column_header_label_map(self):
        """
        Get a map of column header names to column header labels

        :returns: The column map
        :rtype: dict
        """

        col_map = {}
        def_key = self.DEFAULTS['column_header_default_key']

        for key in self.metadata['column_headers']:
            col_map[self.metadata['column_headers'][key][def_key]] = key

        return col_map

    def rename_column_headers_as_names(self):
        """
        Rename the data column headers to their names
        """

        col_map = self.get_column_header_name_map()
        self.data.rename(columns=col_map, inplace=True)

    def rename_column_headers_as_labels(self):
        """
        Rename the data column headers to their labels
        """

        col_map = self.get_column_header_label_map()
        self.data.rename(columns=col_map, inplace=True)

    def store_column_headers(self, parse_metadata=True):
        """
        Store supplementary metadata from the column headers

        The column headers look like:

        ```
        nm1 (u1),nm2 (u2) [nt2],nm3 [nt3],nm4
        ```

        where each column key is the whole string for that column,
        e.g., `k1 = f'{nm1} ({u1})' , k2 = f'{nm2} ({u2}) [{nt2}]'`,
        and so on.

        When `parse_metadata=True`, this will result in:

        ```
        {k1: {'name': nm1, 'units': u1, 'notes': None},
         k2: {'name': nm2, 'units': u2, 'notes': nt2},
         k3: {'name': nm3, 'units': None, 'notes': nt3},
         k4: {'name': nm4, 'units': None, 'notes': None}}
        ```

        whereas with `parse_metadata=False`, this will result in:

        ```
        {k1: {'name': k1, 'units': None, 'notes': None},
         k2: {'name': k2, 'units': None, 'notes': None},
         k3: {'name': k3, 'units': None, 'notes': None},
         k4: {'name': k4, 'units': None, 'notes': None}}
        ```

        :param parse_metadata: Parse each column header value
        :type parse_metadata: bool
        :returns: The column header metadata
        :rtype: dict
        """

        self.metadata['column_headers'] = XCSV.parse_column_headers(self.data.columns, parse_metadata=parse_metadata)

        return self.metadata['column_headers']

    def get_metadata_item(self, key, section='header', default=None):
        """
        Get the value of the given key from the metadata dict,
        or default if not found

        The value can be a simple string, a list of strings, or a dict

        By default, the key is looked for in the 'header' section.  Set
        section='column_headers' to look in the 'column_headers' section
        instead.

        :param key: The header item key
        :type key: str
        :param section: The metadata section.
        One of ['header','column_headers']
        :type section: str
        :param default: The value to return if no matching key exists
        :type default: any
        :returns: The value of the given key or default if not found
        :rtype: any
        """

        if section not in ['header', 'column_headers']:
            raise KeyError(f"Unknown metadata section: {section}")

        try:
            value = self.metadata[section][key]
        except KeyError:
            value = default

        return value

    def get_metadata_item_string(self, key, section='header', default=None):
        """
        Get the original string value of the given key from the metadata dict,
        or default if not found

        If the value is a dict, then it is reconstructed as a string,
        as it would appear in the original file.

        If the value is a list, then its elements are joined into a
        newline-separated string, as it would appear in the original file.

        Otherwise the key's value is returned as-is, a simple string.

        By default, the key is looked for in the 'header' section.  Set
        section='column_headers' to look in the 'column_headers' section
        instead.

        :param key: The header item key
        :type key: str
        :param section: The metadata section.
        One of ['header','column_headers']
        :type section: str
        :param default: The value to return if no matching key exists
        :type default: any
        :returns: The simple value of the given key or default if not found
        :rtype: any
        """

        if section == 'header':
            reconstruct_func = XCSV.reconstruct_file_header_string
        elif section == 'column_headers':
            reconstruct_func = XCSV.reconstruct_column_header_string
        else:
            raise KeyError(f"Unknown metadata section: {section}")

        try:
            value = self.metadata[section][key]

            if isinstance(value, dict):
                value = reconstruct_func(value)

            if isinstance(value, list):
                value = XCSV.recombine_list_header_string(value)
        except KeyError:
            value = default

        return value

    def get_metadata_item_value(self, key, section='header', default=None, cast=False):
        """
        Get the simple value of the given key from the metadata dict,
        or default if not found

        If the value is a dict, then the 'value' member for header items,
        or 'name' member for column_headers items, is returned.

        If the value is a list, then its elements are joined into a
        newline-separated string, as it would appear in the original file.

        If cast is true, then an attempt is made to cast the value to the
        most appropriate numeric primitive type.  One of [int, float].

        Otherwise the key's value is returned as-is, a simple string.

        By default, the key is looked for in the 'header' section.  Set
        section='column_headers' to look in the 'column_headers' section
        instead.

        :param key: The header item key
        :type key: str
        :param section: The metadata section.
        One of ['header','column_headers']
        :type section: str
        :param default: The value to return if no matching key exists
        :type default: any
        :param cast: Cast scalar numeric string value to most appropriate
        primitive type.  One of [int, float]
        :type cast: bool
        :returns: The simple value of the given key or default if not found
        :rtype: any
        """

        if section == 'header':
            subdict_key = self.DEFAULTS['file_header_default_key']
        elif section == 'column_headers':
            subdict_key = self.DEFAULTS['column_header_default_key']
        else:
            raise KeyError(f"Unknown metadata section: {section}")

        try:
            value = self.metadata[section][key]

            if subdict_key in value:
                value = value[subdict_key]

            if isinstance(value, list):
                value = XCSV.recombine_list_header_string(value)

            if cast:
                value = _get_type_cast_value(value)
        except KeyError:
            value = default

        return value

    def get_notes_for_column_header(self, key, default=None):
        """
        Get the string value of the extended header section item that
        corresponds to the 'notes' element of the given column header key,
        or default if not found

        :param key: The column_headers item key
        :type key: str
        :param default: The value to return if no matching key exists
        :type default: any
        :returns: The header value corresponding to the notes element of the
        given column header key or default if not found
        :rtype: any
        """

        value = default
        column_header = self.get_metadata_item(key, section='column_headers')

        if column_header is not None:
            try:
                notes_id = column_header['notes']
            except KeyError:
                notes_id = None

            if notes_id is not None:
                header_key = f"[{notes_id}]"
                value = self.get_metadata_item_string(header_key)

        return value

class Reader(object):
    """
    Class for reading extended CSV data from a file
    """

    def __init__(self, fp=None):
        """
        Constructor

        :param fp: The open file object of the input file
        :type fp: file object
        """

        self.xcsv = None
        self.header = {}
        self.column_headers = {}
        self.data = None

        self.fp = fp

    def set_header_key_value(self, key, value):
        """
        Set the given header key to the given value

        * If the key doesn't already exist in the header, then the key is set
          to the value.
        * If the key already exists in the header and is a scalar type, then
          it is changed into a list and its previous value and the given value
          are stored.
        * If the key is already a list, then the value is appended.

        :param key: The header item key
        :type key: str
        :param value: The header item value
        :type value: str
        """

        if key in self.header:
            if isinstance(self.header[key], list):
                self.header[key].append(value)
            else:
                prev_value = self.header[key]
                self.header[key] = [prev_value, value]
        else:
            self.header[key] = value

        # A value/units dict isn't supported in a list header item, so if
        # we've just added one, raise an exception
        if isinstance(self.header[key], list):
            if isinstance(value, dict):
                note = XCSV._get_list_header_exception_context(self.header[key])
                raise TypeError(note)

    def read_header(self, parse_metadata=True, comment='#', delimiter=':'):
        """
        Read the header from the file

        The extended header section (with default kwargs) looks like:

        ```
        # k1: v1
        # k2: v2 (u2)
        ```

        When `parse_metadata=True`, this will result in:

        ```
        {k1: v1, k2: {'value': v2, 'units': u2}}
        ```

        whereas with `parse_metadata=False`, this will result in:

        ```
        {k1: v1, k2: f'{v2} ({u2})'}
        ```

        Normally we parse a key and a value from each header line.  If a line
        has no key, then it's a continuation line so just take the value and
        append to the previous key as a list.  This will raise an exception
        if no previous key exists.

        A continuation line can be expressed in two forms.

        Simple form - Comment character, no key or delimiter, value:

        ```
        # The second paragraph...
        ```

        Escaped form - Comment character, no key but delimiter, value:

        ```
        # : The second paragraph that may contain delimiter http://...
        ```

        If the effective encoding is UTF-8 and the first line of the input
        begins with a BOM, the BOM is silently skipped

        :param parse_metadata: Parse each header item value
        :type parse_metadata: bool
        :param comment: Comment character of the extended header section
        :type comment: str
        :param delimiter: Key/value delimiter of the extended header section
        :type delimiter: str
        :returns: The header
        :rtype: dict
        """

        key, value = None, None
        self.fp.seek(0, 0)

        for i, line in enumerate(self.fp):
            # UTF-8 encoded text may begin with an unnecessary BOM so skip it
            if i == 0 and self.fp.encoding and encodings.normalize_encoding(self.fp.encoding.lower()) == encodings.normalize_encoding('utf-8'):
                if line.startswith(UTF_8_BOM):
                    line = line[len(UTF_8_BOM):]

            if line.startswith(comment):
                try:
                    left, right = line.split(delimiter, maxsplit=1)
                except ValueError as e:
                    # Value but no key: continuation of previous key
                    if key:
                        value = line.strip().lstrip(comment + ' ')
                    else:
                        raise
                else:
                    left = left.strip().lstrip(comment + ' ')

                    # If left is empty it's an escaped continuation of
                    # previous key, otherwise it's a normal key/value pair
                    if left:
                        key = left

                    value = right.strip()

                if parse_metadata:
                    tokens = XCSV.parse_file_header_tokens(value)

                    if tokens:
                        self.set_header_key_value(key, tokens)
                    else:
                        self.set_header_key_value(key, value)
                else:
                    self.set_header_key_value(key, value)
            else:
                break

        return self.header

    def read_data(self, parse_metadata=True, **kwargs):
        """
        Read the data from the file

        :param parse_metadata: Parse each column header value
        :type parse_metadata: bool
        :param kwargs: Kwargs to pass to the pandas read_csv() function
        :type kwargs: dict
        :returns: The data
        :rtype: pandas.dataframe
        """

        self.fp.seek(0, 0)
        self.data = pd.read_csv(self.fp, **kwargs)
        self.column_headers = XCSV.parse_column_headers(self.data.columns, parse_metadata=parse_metadata)

        return self.data

    def _get_type_cast_missing_value(self):
        """
        Cast a string representation of the missing_value to the most
        appropriate type, if it is present in the extended header section

        :returns: A suitably cast primitive type of the missing_value or None
        :rtype: One of [int, float, str, None]
        """

        value = None
        key = XCSV.DEFAULTS['missing_value_key']

        if key in self.header:
            value = _get_type_cast_value(self.header[key])

        return value

    def mask_missing_values(self):
        """
        Mask any missing values in the data

        Missing values are defined by the missing_value header item

        :returns: The data with any missing values replaced with NaN
        :rtype: pandas.dataframe
        """

        missing_value = self._get_type_cast_missing_value()

        if missing_value is not None:
            self.data.mask(self.data == missing_value, inplace=True)

        return self.data

    def post_process_data(self):
        """
        Optionally post-process the data based on the header

        The following keys are handled:

        * missing_value: Use this to replace any matching data with NaN

        :returns: The (possibly post-processed) data
        :rtype: pandas.dataframe
        """

        self.mask_missing_values()

        return self.data

    def read(self, parse_metadata=True, header_kwargs={'comment': '#', 'delimiter': ':'}, data_kwargs={'comment': '#'}):
        """
        Read the contents from the file

        The extended CSV object is available in the xcsv property

        If `parse_metadata=True`, then the metadata are parsed.  Depending
        on the presence of certain keys in the header section, these are used
        to further post-process the data.  See `post_process_data()`.

        :param parse_metadata: Parse the header and column headers metadata
        :type parse_metadata: bool
        :param header_kwargs: Kwargs to pass to the read_header() function
        :type header_kwargs: dict
        :param data_kwargs: Kwargs to pass to the read_data() function,
        and on to the pandas read_csv() function
        :type data_kwargs: dict
        :returns: The extended CSV object
        :rtype: XCSV
        """

        self.read_header(parse_metadata=parse_metadata, **header_kwargs)
        self.read_data(parse_metadata=parse_metadata, **data_kwargs)

        if parse_metadata:
            self.post_process_data()

        metadata = {'header': self.header, 'column_headers': self.column_headers}
        self.xcsv = XCSV(metadata=metadata, data=self.data)

        return self.xcsv

    def read_as_json(self, data_kwargs={}):
        """
        Read the contents from the file as a JSON-serialized XCSV object

        The extended CSV object is available in the xcsv property

        :param data_kwargs: Kwargs to pass to the pandas read_json() function
        :type data_kwargs: dict
        :returns: The extended CSV object
        :rtype: XCSV
        """

        # Load the JSON data, pull out the metadata dict, and store
        obj = json.load(self.fp)
        metadata = obj['metadata']
        self.header = metadata['header']
        self.column_headers = metadata['column_headers']

        # Convert the data (pandas DataFrame) back to JSON and deserialize
        jdata = json.dumps(obj['data'])
        self.data = pd.read_json(io.StringIO(jdata), **data_kwargs)

        # Combine the metadata and data into an XSV object
        self.xcsv = XCSV(metadata=metadata, data=self.data)

        return self.xcsv

class Writer(object):
    """
    Class for writing extended CSV data to a file
    """

    def __init__(self, fp=None, xcsv=None):
        """
        Constructor

        :param fp: The open file object of the output file
        :type fp: file object
        :param xcsv: The extended CSV object to be written out
        :type xcsv: XCSV
        """

        self.header = {}
        self.column_headers = {}
        self.data = None

        self.fp = fp
        self.xcsv = xcsv

        self.store_components()

    def store_components(self):
        """
        Extract the components of the extended CSV object and store in this
        object's header, column_headers and data
        """

        if self.xcsv:
            self.header = self.xcsv.metadata['header']
            self.column_headers = self.xcsv.metadata['column_headers']
            self.data = self.xcsv.data

    def format_header_line(self, comment, key, delimiter, value):
        """
        Format a header line from the given components

        :param comment: Comment character of the extended header section
        :type comment: str
        :param key: The header item key
        :type key: str
        :param delimiter: Key/value delimiter of the extended header section
        :type delimiter: str
        :param value: The header item value
        :type value: str
        :returns: The formatted header line
        :rtype: str
        """

        return '{}{}{}{}'.format(comment, key, delimiter, value)

    def header_value_as_string(self, value):
        """
        Convert the given header value to a string

        If the given header value is a dict, then the elements are recombined
        into the original formatted string, otherwise the header value is
        already a string and so is used as-is

        :param value: The header item value
        :type value: dict or str
        :returns: The original header line value
        :rtype: str
        """

        s = ''

        if isinstance(value, dict):
            s = XCSV.reconstruct_file_header_string(value)
        else:
            s = value

        return s

    def reconstruct_header_lines(self, comment, delimiter):
        """
        Reconstruct the raw header lines from the parsed header

        :param comment: Comment character of the extended header section
        :type comment: str
        :param delimiter: Key/value delimiter of the extended header section
        :type delimiter: str
        :returns: The reconstructed raw header lines
        :rtype: list
        """

        header_lines = []

        for key, value in self.header.items():
            if isinstance(value, list):
                # This header item is made up of a key and continuation lines
                for i, element in enumerate(value):
                    if i == 0:
                        line = self.format_header_line(comment, key, delimiter, self.header_value_as_string(element))
                    else:
                        # If the value contains the delimiter, then we have
                        # to create an escaped continuation line, e.g.
                        # # : The continuation value: <- with delimiter
                        value_str = self.header_value_as_string(element)
                        cont_key = ''
                        cont_delimiter = delimiter if delimiter.strip() in value_str else ''
                        line = self.format_header_line(comment, cont_key, cont_delimiter, value_str)

                    header_lines.append(line)
            else:
                line = self.format_header_line(comment, key, delimiter, self.header_value_as_string(value))
                header_lines.append(line)

        return header_lines

    def write_header(self, comment='# ', delimiter=': '):
        """
        Write the header to the file

        N.B.: The default comment and delimiter have single-space right-padding
        to make it more comfortable when reading by humans.  This isn't a
        problem, as all leading/trailing space is stripped when reading an
        extended CSV file

        :param comment: Comment character of the extended header section
        :type comment: str
        :param delimiter: Key/value delimiter of the extended header section
        :type delimiter: str
        :returns: The header
        :rtype: dict
        """

        for line in self.reconstruct_header_lines(comment, delimiter):
            self.fp.write(f'{line}\n')

        return self.header

    def write_data(self, **kwargs):
        """
        Write the data to the file

        :param kwargs: Kwargs to pass to the DataFrame to_csv() function
        :type kwargs: dict
        :returns: The data
        :rtype: pandas.dataframe
        """

        self.data.to_csv(self.fp, **kwargs)

        return self.data

    def write(self, fp=None, xcsv=None, header_kwargs={'comment': '# ', 'delimiter': ': '}, data_kwargs={'index': False}):
        """
        Write the contents to the file

        :param fp: The open file object of the output file.  If not
        provided here, then it should have been set in the constructor
        :type fp: file object
        :param xcsv: The extended CSV object to be written out.  If not
        provided here, then it should have been set in the constructor
        :type xcsv: XCSV
        :param header_kwargs: Kwargs to pass to the write_header() function
        :type header_kwargs: dict
        :param data_kwargs: Kwargs to pass to the write_data() function,
        and on to the DataFrame to_csv() function
        :type data_kwargs: dict
        :returns: The extended CSV object
        :rtype: XCSV
        """

        if fp:
            self.fp = fp

        if xcsv:
            self.xcsv = xcsv

        self.store_components()

        self.write_header(**header_kwargs)
        self.write_data(**data_kwargs)

        return self.xcsv

    def write_as_json(self, fp=None, xcsv=None, data_kwargs={}):
        """
        Write the contents to the file as a JSON-serialized XCSV object

        :param fp: The open file object of the output file.  If not
        provided here, then it should have been set in the constructor
        :type fp: file object
        :param xcsv: The extended CSV object to be written out.  If not
        provided here, then it should have been set in the constructor
        :type xcsv: XCSV
        :param data_kwargs: Kwargs to pass to the DataFrame to_json() function
        :type data_kwargs: dict
        :returns: The extended CSV object
        :rtype: XCSV
        """

        if fp:
            self.fp = fp

        if xcsv:
            self.xcsv = xcsv

        self.store_components()

        jdata = json.loads(self.xcsv.data.to_json(None, **data_kwargs))
        json.dump({'metadata': self.xcsv.metadata, 'data': jdata}, self.fp)

        return self.xcsv

class File(object):
    """
    Context manager for reading and writing extended CSV files
    """

    DEFAULTS = {
        'file_encoding': 'utf-8',
        'suffix': '.csv',
    }

    def __init__(self, path=None, **kwargs):
        """
        Constructor

        :param path: Path to the file
        :type path: str
        :param kwargs: Keyword arguments for the open function
        :type kwargs: kwargs
        """

        self.path = path
        self.kwargs = kwargs
        self.fp = None
        self.reader = None
        self.writer = None
        self.xcsv = None

    def __enter__(self):
        """
        Enter the runtime context for this object

        The file is opened

        :returns: This object
        :rtype: xcsv.File
        """

        return self.open(path=self.path, **self.kwargs)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Exit the runtime context for this object

        The file is closed

        :returns: False
        :rtype: bool
        """

        self.close()

        return False         # This ensures any exception is re-raised

    def open(self, path=None, mode='r', encoding='utf-8'):
        """
        Open the given file

        :param path: Path to the file
        :type path: str
        :param mode: Mode in which to open the file
        :type mode: str
        :param encoding: Encoding of the file
        :type encoding: str
        :returns: This object
        :rtype: xcsv.File
        """

        if path:
            self.path = path

        self.fp = open(self.path, mode, encoding=encoding)

        return self

    def close(self):
        """
        Close the file

        :returns: This object
        :rtype: xcsv.File
        """

        self.fp.close()
        self.fp = None

        return self

    def read(self, parse_metadata=True):
        """
        Reads the contents of the extended CSV file

        The extended CSV object is available in the xcsv property

        :param parse_metadata: Parse the header and column headers metadata
        :type parse_metadata: bool
        :returns: The extended CSV object
        :rtype: XCSV
        """

        self.reader = Reader(fp=self.fp)
        self.xcsv = self.reader.read(parse_metadata=parse_metadata)

        return self.xcsv

    def write(self, xcsv=None):
        """
        Writes the contents of the extended CSV file

        :param xcsv: The extended CSV object to be written out
        :type xcsv: XCSV
        :returns: The extended CSV object
        :rtype: XCSV
        """

        if xcsv:
            self.xcsv = xcsv

        self.writer = Writer(fp=self.fp, xcsv=self.xcsv)
        self.writer.write()

        return self.xcsv

