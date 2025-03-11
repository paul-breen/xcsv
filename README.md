# xcsv

xcsv is a package for reading and writing extended CSV files.

## Extended CSV format

* Extended header section of parseable atttributes, introduced by '#'.
* Header row of variable name and units for each column.
* Data rows.

### Discussion

#### Extended header section

* No leading/trailing whitespace.
* Each line introduced by a comment ('#') character.
* Each line contains a single header item, or a single element of a multi-line list header item.
* Key/value separator ': '.
* Multi-line values naturally continued over to the next lines following the line introducing the key.
* Continuation lines that contain the delimiter character in the value must be escaped by a leading delimiter.
* Preferably use a common vocabulary for attribute name, such as [CF conventions](http://cfconventions.org/index.html).
* Preferably include recommended attributes from [Attribute Convention for Data Discovery (ACDD)](https://wiki.esipfed.org/Attribute_Convention_for_Data_Discovery_1-3).
* Preferably use units from [Unified Code for Units of Measure](https://ucum.org/ucum.html) and/or [Udunits](https://www.unidata.ucar.edu/software/udunits/).
* Units in parentheses.
* Units are automatically parsed when they appear in parentheses at the end of a line.  Hence, if you have non-units text in parentheses at the end of the line (e.g. when expanding an acronym), then ensure that the line doesn't end with a closing parenthesis to avoid the text being incorrectly parsed as units.  A '.' would suffice.
  + This line: `# latitude: -73.86 (degree_north)` would parse correctly as a value/units dict: `'latitude': {'value': '-73.86', 'units': 'degree_north'}`.
  + This line: `# institution: BAS (British Antarctic Survey).` would correctly avoid being parsed as a value/units dict because of the '.' as the last character.
* Certain special keys are used to [further process the data](#automated-post-processing-of-the-data), for example the `missing_value` key.

##### Example extended header section

```
# id: 1
# title: The title
# summary: This dataset...
# The second summary paragraph.
# : The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain
# authors: A B, C D
# institution: BAS (British Antarctic Survey).
# latitude: -73.86 (degree_north)
# longitude: -65.46 (degree_east)
# elevation: 1897 (m a.s.l.)
# [a]: 2012 not a complete year
```

#### Header row

* No leading/trailing whitespace.
* Preferably use a common vocabulary for variable name, such as [CF conventions](http://cfconventions.org/index.html).
* Units in parentheses.
* Optional notes in square brackets, that reference an item in the extended header section.

##### Example header row

```
time (year) [a],depth (m)
```

#### Data row

* No leading/trailing whitespace.

##### Example data row

```
2012,0.575
```

#### Automated post-processing of the data

Depending on the presence of special keys in the extended header section, these will be used to automatically post-process the data.  To turn off this automatic behaviour, either remove or rename these keys, or set `parse_metadata=False` when reading in the data.

* `missing_value`:  This is used to define those values in the data that are to be considered as missing values.  This is typically a value that is outside the domain of the data such as `-999.99`, or can be a symbolic value such as `NA`.  All such values appearing in the data will be masked, appearing as an `NA` value to pandas (i.e. `pd.isna(value) == True`).  Note that pandas itself will automatically do this for certain values regardless of this key, such as for the strings `NaN` or `NA`, or the constant `None`.

#### A note on encodings

The default character set encoding is UTF-8, without a Byte Order Mark (BOM).  If an extended CSV file has a different encoding, it can either be converted to UTF-8 (by using `iconv`, for example), or the encoding can be specified when opening the file (`xcsv.File(filename, encoding=encoding)`).

If the encoding of a file is UTF-8 and it begins with a BOM, then the BOM is silently skipped.  This is necessary so that the extended header section is parsed correctly.

## Install

The package can be installed from PyPI:

```bash
$ pip install xcsv
```

## Using the package

The package has a general `XCSV` class, that has a `metadata` attribute that holds the parsed contents of the extended file header section and the parsed column headers from the data table, and a `data` attribute that holds the data table (including the column headers as-is).

The `metadata` attribute is a dict, with the following general structure:

```python
{'header': {}, 'column_headers': {}}
```

and the `data` attribute is a pandas DataFrame, and so has all the features of the [pandas](https://pandas.pydata.org/docs/index.html) package.

The package also has a `Reader` class for reading an extended CSV file into an XCSV object, and similarly a `Writer` class for writing an XCSV object to a file in the extended CSV format.  In addition there is a `File` class that provides a convenient context manager for reading and writing these files.

### Integrating the package with other software

Even though the primary focus of the xcsv package is to produce self-describing tabular datasets, it can also read and write serialised JSON views of an XCSV object.  This is most useful when integrating XCSV data into some other software workflow.

To customise the integration when reading JSON data, any kwargs supported by `pandas.read_json()` can be passed in `data_kwargs` when calling `Reader.read_as_json()`.  Similarly when writing JSON data, any kwargs supported by `pandas.DataFrame.to_json()` can be passed in `data_kwargs` when calling `Writer.write_as_json()`.

For example, the default serialisation form is the pandas default for DataFrames (`columns`), but any serialisation form can be used by specifying the `orient` kwarg:

```python
    with open('out.json', mode='w') as fp:
        writer = xcsv.Writer(fp=fp, xcsv=dataset)
        writer.write_as_json(data_kwargs={'orient': 'table'})
```

### Examples

#### Simple read and print

Read in a file and print the contents to `stdout`.  This shows how the contents of the extended CSV file are stored in the XCSV object.  Note how multi-line values, such as `summary` here, are stored in a list.  Given the following script called, say, `simple_read.py`:

```python
import argparse
import pprint

import xcsv

parser = argparse.ArgumentParser()
parser.add_argument('filename', help='filename.csv')
args = parser.parse_args()

with xcsv.File(args.filename) as f:
    dataset = f.read()
    pprint.pp(dataset.metadata)
    print(dataset.data)
```

Running it would produce:

```bash
$ python3 simple_read.py example.csv
{'header': {'id': '1',
            'title': 'The title',
            'summary': ['This dataset...',
                        'The second summary paragraph.',
                        'The third summary paragraph.  Escaped because it '
                        'contains the delimiter in a URL https://dummy.domain'],
            'authors': 'A B, C D',
            'institution': 'BAS (British Antarctic Survey).',
            'latitude': {'value': '-73.86', 'units': 'degree_north'},
            'longitude': {'value': '-65.46', 'units': 'degree_east'},
            'elevation': {'value': '1897', 'units': 'm a.s.l.'},
            '[a]': '2012 not a complete year'},
 'column_headers': {'time (year) [a]': {'name': 'time',
                                        'units': 'year',
                                        'notes': 'a'},
                    'depth (m)': {'name': 'depth',
                                  'units': 'm',
                                  'notes': None}}}
   time (year) [a]  depth (m)
0             2012      0.575
1             2011      1.125
2             2010      2.225
```

#### Simple read and print with missing values

If the above example header section included the following:

```
# missing_value: -999.99
```

and the data section looked like:

```
time (year) [a],depth (m)
2012,0.575
2011,1.125
2010,2.225
2009,-999
2008,999
2007,-999.99
2006,999.99
2005,NA
2004,NaN
```

Running it would produce:

```bash
$ python3 simple_read.py missing_example.csv
{'header': {'id': '1',
            'title': 'The title',
            'summary': ['This dataset...',
                        'The second summary paragraph.',
                        'The third summary paragraph.  Escaped because it '
                        'contains the delimiter in a URL https://dummy.domain'],
            'authors': 'A B, C D',
            'institution': 'BAS (British Antarctic Survey).',
            'latitude': {'value': '-73.86', 'units': 'degree_north'},
            'longitude': {'value': '-65.46', 'units': 'degree_east'},
            'elevation': {'value': '1897', 'units': 'm a.s.l.'},
            'missing_value': '-999.99',
            '[a]': '2012 not a complete year'},
 'column_headers': {'time (year) [a]': {'name': 'time',
                                        'units': 'year',
                                        'notes': 'a'},
                    'depth (m)': {'name': 'depth',
                                  'units': 'm',
                                  'notes': None}}}
   time (year) [a]  depth (m)
0             2012      0.575
1             2011      1.125
2             2010      2.225
3             2009   -999.000
4             2008    999.000
5             2007        NaN
6             2006    999.990
7             2005        NaN
8             2004        NaN
```

Note that the `-999.99` value has been automatically masked as a missing value (shown as `NaN` in the printed pandas DataFrame), as well as the `NA` and `NaN` strings in the original data, which pandas automatically masks itself, irrespective of the `missing_value` header item.

#### Simple read and plot

Read a file and plot the data:

```python
import argparse

import matplotlib.pyplot as plt

import xcsv

parser = argparse.ArgumentParser()
parser.add_argument('filename', help='filename.csv')
args = parser.parse_args()

with xcsv.File(args.filename) as f:
    dataset = f.read()
    dataset.data.plot(x='depth (m)', y='time (year) [a]')
    plt.show()
```

#### Simple read and write

Read a file in, manipulate the data in some way, and write this modified XCSV object out to a new file:

```python
import argparse

import xcsv

parser = argparse.ArgumentParser()
parser.add_argument('in_filename', help='in_filename.csv')
parser.add_argument('out_filename', help='out_filename.csv')
args = parser.parse_args()

with xcsv.File(args.in_filename) as f:
    dataset = f.read()

# Manipulate the data...

with xcsv.File(args.out_filename, mode='w') as f:
    f.write(xcsv=dataset)
```

#### Construct an XCSV object from data

Construct the metadata and data as python objects and combine into an XCSV object:

```python
import pprint

import pandas as pd

import xcsv

# Construct the header dict and data pandas DataFrame
header = {
    'id': '123',
    'title': 'Temperature timeseries',
    'summary': 'This dataset comprises temperature timeseries from...',
    'longitude': {'value': '-73.06', 'units': 'degree_east'},
    'latitude': {'value': '-74.33', 'units': 'degree_north'}
}
data = pd.DataFrame({
    'time (day)': [1,2,3,4,5],
    'temperature (deg_C)': [-3.5,-3.2,-2.9,-3.1,-2.8]
})

# Add the header and a placeholder for the column headers to the metadata dict
metadata = {'header': header, 'column_headers': {}}

dataset = xcsv.XCSV(metadata=metadata, data=data)

# Parse the column headers from the DataFrame and store in
# dataset.metadata['column_headers']
dataset.store_column_headers()

pprint.pp(dataset.metadata)
print(dataset.data)
```

Running it would produce:

```bash
$ python3 construct_xcsv.py
{'header': {'id': '123',
            'title': 'Temperature timeseries',
            'summary': 'This dataset comprises temperature timeseries from...',
            'longitude': {'value': '-73.06', 'units': 'degree_east'},
            'latitude': {'value': '-74.33', 'units': 'degree_north'}},
 'column_headers': {'time (day)': {'name': 'time',
                                   'units': 'day',
                                   'notes': None},
                    'temperature (deg_C)': {'name': 'temperature',
                                            'units': 'deg_C',
                                            'notes': None}}}
   time (day)  temperature (deg_C)
0           1                 -3.5
1           2                 -3.2
2           3                 -2.9
3           4                 -3.1
4           5                 -2.8
```

As a convenience, we could use XCSV to parse value/units dicts from header item string values:

```python
    'longitude': xcsv.XCSV.parse_file_header_tokens('-73.06 (degree_east)'),
    'latitude': xcsv.XCSV.parse_file_header_tokens('-74.33 (degree_north)')
```

Instead of printing to stdout, we could write the constructed XCSV object as an XCSV file:

```python
    with xcsv.File('out.csv', mode='w') as f:
        f.write(dataset)
```

which would produce:

```bash
$ cat out.csv
# id: 123
# title: Temperature timeseries
# summary: This dataset comprises temperature timeseries from...
# longitude: -73.06 (degree_east)
# latitude: -74.33 (degree_north)
time (day),temperature (deg_C)
1,-3.5
2,-3.2
3,-2.9
4,-3.1
5,-2.8
```

