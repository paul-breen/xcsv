###############################################################################
# Project: Extended CSV common file format
# Purpose: Classes to encapsulate an extended CSV file
# Author:  Paul M. Breen
# Date:    2022-04-14
###############################################################################

__version__ = '0.2.0'

import re
import argparse

import pandas as pd

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

class XCSV(object):
    """
    Class for an extended CSV object
    """

    DEFAULTS = {
        'file_header_default_key': 'value',
        'file_header_pattern': r'(?P<value>.+)\s+\((?P<units>.+)\)$',
        'file_header_template': '{value} ({units})',
        'column_header_default_key': 'name',
        'column_header_pattern': r'(?P<name>[^][)(]+)(\s+\((?P<units>.+)\))?(\s+\[(?P<notes>.+)\])?$',
        'column_header_template': '{name} ({units}) [{notes}]'
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

    @classmethod
    def parse_file_header_tokens(cls, s):
        """
        Parse value and units from the given file header value string
        See `cls.DEFAULTS['file_header_pattern']` and `_parse_tokens()`
        """

        pattern = cls.DEFAULTS['file_header_pattern']

        return _parse_tokens(s, pattern)

    @classmethod
    def parse_column_header_tokens(cls, s):
        """
        Parse name, units and notes from the given column header string
        See `cls.DEFAULTS['column_header_pattern']` and `_parse_tokens()`
        """

        pattern = cls.DEFAULTS['column_header_pattern']

        return _parse_tokens(s, pattern)

    @classmethod
    def reconstruct_file_header_string(cls, d):
        """
        Reconstruct the header value string from the given dict
        See `cls.DEFAULTS['file_header_template']`
        """

        template = cls.DEFAULTS['file_header_template']

        return template.format(**d)

    @classmethod
    def reconstruct_column_header_string(cls, d):
        """
        Reconstruct the column header string from the given dict
        See `cls.DEFAULTS['column_header_template']`
        """

        template = cls.DEFAULTS['column_header_template']

        return template.format(**d)

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

    def read_header(self, comment='#', delimiter=':', parse_metadata=True):
        """
        Read the header from the file

        The extended header section (with default kwargs) looks like:

        # k1: v1
        # k2: v2 (u2)

        When `parse_metadata=True`, this will result in:

        {k1: v1, k2: {'value': v2, 'units': u2}}

        whereas with `parse_metadata=False`, this will result in:

        {k1: v1, k2: f'{v2} ({u2})'}

        Normally we parse a key and a value from each header line.  If a line
        has no key, then it's a continuation line so just take the value and
        append to the previous key as a list.  This will raise an exception
        if no previous key exists.

        A continuation line can be expressed in two forms.

        Simple form - Comment character, no key or delimiter, value:
        # The second paragraph...

        Escaped form - Comment character, no key but delimiter, value:
        # : The second paragraph that may contain delimiter http://...

        :param comment: Comment character of the extended header section
        :type comment: str
        :param delimiter: Key/value delimiter of the extended header section
        :type delimiter: str
        :param parse_metadata: Parse each header item value
        :type parse_metadata: bool
        :returns: The header
        :rtype: dict
        """

        key, value = None, None
        self.fp.seek(0, 0)

        for line in self.fp:
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

    def _store_column_headers(self, parse_metadata=True):
        """
        Store supplementary metadata from the column headers

        The column headers look like:

        nm1 (u1),nm2 (u2) [nt2],nm3 [nt3],nm4

        where each column key is the whole string for that column,
        e.g., k1 = f'{nm1} ({u1})' , k2 = f'{nm2} ({u2}) [{nt2}]', and so on.

        When `parse_metadata=True`, this will result in:

        {k1: {'name': nm1, 'units': u1, 'notes': None},
         k2: {'name': nm2, 'units': u2, 'notes': nt2},
         k3: {'name': nm3, 'units': None, 'notes': nt3},
         k4: {'name': nm4, 'units': None, 'notes': None}}

        whereas with `parse_metadata=False`, this will result in:

        {k1: {'name': k1, 'units': None, 'notes': None},
         k2: {'name': k2, 'units': None, 'notes': None},
         k3: {'name': k3, 'units': None, 'notes': None},
         k4: {'name': k4, 'units': None, 'notes': None}}

        :param parse_metadata: Parse each column header value
        :type parse_metadata: bool
        :returns: The column header metadata
        :rtype: dict
        """

        def_key = XCSV.DEFAULTS['column_header_default_key']

        for col in self.data.columns:
            if parse_metadata:
                tokens = XCSV.parse_column_header_tokens(col)

                try:
                    self.column_headers[col] = tokens
                except KeyError:
                    pass
            else:
                self.column_headers[col] = {def_key: col}

        return self.column_headers

    def read_data(self, comment='#', parse_metadata=True):
        """
        Read the data from the file

        :param comment: Comment character of the extended header section
        :type comment: str
        :param parse_metadata: Parse each column header value
        :type parse_metadata: bool
        :returns: The data
        :rtype: pandas.dataframe
        """

        self.fp.seek(0, 0)
        self.data = pd.read_csv(self.fp, comment=comment)
        self._store_column_headers(parse_metadata=parse_metadata)

        return self.data

    def read(self, parse_metadata=True):
        """
        Read the contents from the file

        The extended CSV object is available in the xcsv property

        :param parse_metadata: Parse the header and column headers metadata
        :type parse_metadata: bool
        :returns: The extended CSV object
        :rtype: XCSV
        """

        self.read_header(parse_metadata=parse_metadata)
        self.read_data(parse_metadata=parse_metadata)
        metadata = {'header': self.header, 'column_headers': self.column_headers}
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

    def write_data(self):
        """
        Write the data to the file

        :returns: The data
        :rtype: pandas.dataframe
        """

        self.data.to_csv(self.fp, index=False)

        return self.data

    def write(self, fp=None, xcsv=None):
        """
        Write the contents to the file

        :param fp: The open file object of the output file.  If not
        provided here, then it should have been set in the constructor
        :type fp: file object
        :param xcsv: The extended CSV object to be written out.  If not
        provided here, then it should have been set in the constructor
        :type xcsv: XCSV
        :returns: The extended CSV object
        :rtype: XCSV
        """

        if fp:
            self.fp = fp

        if xcsv:
            self.xcsv = xcsv

        self.header = self.xcsv.metadata['header']
        self.column_headers = self.xcsv.metadata['column_headers']
        self.data = self.xcsv.data

        self.write_header()
        self.write_data()

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

