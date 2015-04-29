#!/usr/bin/env python
"""
Aggregate the requests of all filenames piped into stdin and write the
results back to stdout.
"""
import csv
import sys
import os
import fileinput

DELIMITER = os.getenv('DELIMITER', ' ')


def ensure_value(dictionary, z, y, x, default_value=0):
    """Make sure the multidimensional dictionary always has a default value"""
    if z not in dictionary:
        dictionary[z] = {}

    if y not in dictionary[z]:
        dictionary[z][y] = {}

    if x not in dictionary[z][y]:
        dictionary[z][y][x] = default_value

    return dictionary


def add_requests(tiles, csv_file):
    """Read rqeuests of file and add them to the existing tile entries"""
    reader = csv.reader(csv_file, delimiter=DELIMITER)

    for row in reader:
        z = int(row[0])
        x = int(row[1])
        y = int(row[2])
        requests = int(row[3])

        ensure_value(tiles, z, y, x)
        tiles[z][y][x] += requests


if __name__ == '__main__':
    writer = csv.writer(sys.stdout, delimiter=DELIMITER)
    tiles = {}

    for filepath in fileinput.input():
        with open(filepath.strip()) as csv_file:
            add_requests(tiles, csv_file)

    for z in tiles:
        for y in tiles[z]:
            for x in tiles[z][y]:
                requests = tiles[z][y][x]
                writer.writerow([z, x, y, requests])
