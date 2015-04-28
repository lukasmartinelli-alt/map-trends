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


def fill_dict(dictionary, z, y, x):
    if z not in dictionary:
        dictionary[z] = {}

    if y not in dictionary[z]:
        dictionary[z][y] = {}

    if x not in dictionary[z][y]:
        dictionary[z][y][x] = 0

    return dictionary


if __name__ == '__main__':
    reader = csv.reader(sys.stdin, delimiter=DELIMITER)
    writer = csv.writer(sys.stdout, delimiter=DELIMITER)

    last_zoom = 0
    tiles = {}

    for row in reader:
        z = int(row[0])
        x = int(row[1])
        y = int(row[2])
        requests = int(row[3])

        children = mercantile.children(x, y, z)
        for child in children:
            fill_dict(tiles, child.z, child.y, child.x)
            tiles[child.z][child.y][child.x] = requests

        if z > 0:
            fill_dict(tiles, z, y, x)
            tiles[z][y][x] += requests

    for z in tiles:
        for y in tiles[z]:
            for x in tiles[z][y]:
                requests = tiles[z][y][x]
                center = calculate_center(x, y, z)
                writer.writerow([z, x, y, requests] + list(center))
