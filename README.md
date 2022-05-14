# xcsv

xcsv is a package for reading and writing extended CSV files.

## Extended CSV format

* Extended header section of parseable atttributes, introduced by '#'.
* Header row of variable and units for each column.
* Data rows.

### Example

#### Extended header section

* No leading/trailing whitespace.
* Each line introduced by a comment ('#') character.
* Each line contains a single header item.
* Key/value separator ': '.
* Multi-line values naturally continued over to the next lines following the line introducing the key.
* Continuation lines that contain the delimiter character in the value must be escaped by a leading delimiter.
* Preferably use a common vocabulary for attribute name, such as [CF conventions](http://cfconventions.org/index.html).
* Preferably include recommended attributes from [Attribute Convention for Data Discovery (ACDD)](https://wiki.esipfed.org/Attribute_Convention_for_Data_Discovery_1-3).
* Preferably use units from [Unified Code for Units of Measure](https://ucum.org/ucum.html) and/or [Udunits](https://www.unidata.ucar.edu/software/udunits/).
* Units in parentheses.

```
# id: 1
# title: The title
# summary: This dataset...
# The second summary paragraph.
# : The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain
# authors: A B, C D
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

```
time (year) [a],depth (m)
```

#### Data row

* No leading/trailing whitespace.

```
2012,0.575
```

## Install

The package can be installed from PyPI:

```bash
$ pip install xcsv
```

## Using the package

The package has a general `XCSV` class, that has a `metadata` attribute that holds the parsed contents of the extended file header section and the parsed column headers from the data table, and a `data` attribute that holds the data table (including the column headers as-is).

The `metadata` attribute is a `dict`, with the following general structure:

```python
{'header': {}, 'column_headers': {}}
```

and the `data` attribute is a `pandas.DataFrame`, and so has all the features of the [pandas](https://pandas.pydata.org/docs/index.html) package.

The package also has a `Reader` class for reading an extended CSV file into an `XCSV` object, and similarly a `Writer` class for writing an `XCSV` object to a file in the extended CSV format.  In addition there is a `File` class that provides a convenient context manager for reading and writing these files.

### Examples

#### Simple read and print

Read in a file and print the contents to `stdout`.  This shows how the contents of the extended CSV file are stored in the `XCSV` object.  Note how multi-line values, such as `summary` here, are stored in a list.  Given the following script called, say, `simple_read.py`:

```python
import argparse

import xcsv

parser = argparse.ArgumentParser()
parser.add_argument('filename', help='filename.csv')
args = parser.parse_args()

with xcsv.File(args.filename) as f:
    content = f.read()
    print(content.metadata)
    print(content.data)
```

Running it would produce:

```bash
$ python3 simple_read.py example.csv
{'header': {'id': '1', 'title': 'The title', 'summary': ['This dataset...', 'The second summary paragraph.', 'The third summary paragraph.  Escaped because it contains the delimiter in a URL https://dummy.domain'], 'authors': 'A B, C D', 'latitude': {'value': '-73.86', 'units': 'degree_north'}, 'longitude': {'value': '-65.46', 'units': 'degree_east'}, 'elevation': {'value': '1897', 'units': 'm a.s.l.'}, '[a]': '2012 not a complete year'}, 'column_headers': {'time (year) [a]': {'name': 'time', 'units': 'year', 'notes': 'a'}, 'depth (m)': {'name': 'depth', 'units': 'm', 'notes': None}}}
   time (year) [a]  depth (m)
0             2012      0.575
1             2011      1.125
2             2010      2.225
```

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
    content = f.read()
    content.data.plot(x='depth (m)', y='time (year) [a]')
    plt.show()
```

#### Simple read and write

Read a file in, manipulate the data in some way, and write this modified `XCSV` object out to a new file:

```python
import argparse

import xcsv

parser = argparse.ArgumentParser()
parser.add_argument('in_filename', help='in_filename.csv')
parser.add_argument('out_filename', help='out_filename.csv')
args = parser.parse_args()

with xcsv.File(args.in_filename) as f:
    content = f.read()

# Manipulate the data...

with xcsv.File(args.out_filename, mode='w') as f:
    f.write(xcsv=content)
```

