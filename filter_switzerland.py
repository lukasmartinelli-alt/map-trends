#!/usr/bin/env python
"""
Filter out all points in Switzerland
"""
import csv
import sys
import os
from decimal import *

DELIMITER = os.getenv('DELIMITER', ' ')
NORTH = Decimal('47.9922193487799')
WEST = Decimal('5.99235534667969')
EAST = Decimal('11.1243438720703')
SOUTH = Decimal('45.6769214851596')


def in_switzerland(coords):
    lat, lng = coords
    return lat < NORTH and lat > SOUTH and lng > WEST and lng < EAST


if __name__ == '__main__':
    reader = csv.reader(sys.stdin, delimiter=DELIMITER)
    writer = csv.writer(sys.stdout, delimiter=DELIMITER)

    for row in reader:
        requests = int(row[0])
        lat = Decimal(row[1])
        lng = Decimal(row[2])

        if in_switzerland((lat, lng)):
            writer.writerow([requests, lat, lng])
