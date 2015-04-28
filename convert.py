import csv
import sys
import os
import mercantile

DELIMITER = os.getenv('DELIMITER', ' ')


def calculate_center(x, y, zoom):
    bounds = mercantile.bounds(x, y, zoom)
    height = bounds.north - bounds.south
    width = bounds.east - bounds.west
    center = (bounds.north + height / 2, bounds.west + width / 2)

    return center


if __name__ == '__main__':
    reader = csv.reader(sys.stdin, delimiter=DELIMITER)
    writer = csv.writer(sys.stdout, delimiter=DELIMITER)

    for row in reader:
        zoom = int(row[0])
        x = int(row[1])
        y = int(row[2])
        requests = int(row[3])

        center = calculate_center(x, y, zoom)

        writer.writerow([zoom, x, y, requests] + list(center))
