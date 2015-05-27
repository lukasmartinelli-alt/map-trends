import argparse
import collections
import datetime
import sys

import mercantile


MIN_DATE = '0000-00-00'
MAX_DATE = '9999-99-99'
MIN_ZOOM = 0
MAX_ZOOM = 19

cache_down = {}
cache_up = {}
cache_center = {}


def get_down_tiles(x, y, z, target_zoom):
    assert z <= target_zoom, 'target zoom less than zoom %s <= %s' % (z, target_zoom)
    k = (x, y, z, target_zoom)
    if k not in cache_down:
        if z == target_zoom:
            result = [(x, y, z)]
        else:
            result = []
            for t in mercantile.children(x, y, z):
                result += get_down_tiles(t.x, t.y, t.z, target_zoom)
        cache_down[k] = tuple(result)
        return result
    return cache_down[k]


def get_up_tile(x, y, z, target_zoom):
    assert z >= target_zoom, 'target zoom more than zoom %s >= %s' % (z, target_zoom)
    k = (x, y, z, target_zoom)
    if k not in cache_up:
        if z == target_zoom:
            result = (x, y, z)
        else:
            t = mercantile.parent(x, y, z)
            result = get_up_tile(t.x, t.y, t.z, target_zoom)
        cache_up[k] = result
        return result
    return cache_up[k]


def calculate_center(x, y, z):
    k = (x, y, z)
    if k not in cache_center:
        bounds = mercantile.bounds(x, y, z)
        height = bounds.north - bounds.south
        width = bounds.east - bounds.west
        center = (bounds.north + height / 2, bounds.west + width / 2)
        cache_center[k] = center
        return center
    return cache_center[k]


def flush(stdout, tiles, min_count, max_count):
    for k, count in tiles.items():
        if min_count and count < min_count:
            continue
        if max_count and count > max_count:
            continue
        date, z, x, y = k
        lat, lon = calculate_center(x, y, z)
        stdout.write(('%s,%s,%s,%s\n' % (count, date, lat, lon)).encode())
    return collections.defaultdict(int)


def split(stdin, stdout,
          date_from=None, date_to=None,
          min_count=None, max_count=None,
          min_zoom=None, max_zoom=None,
          min_subz=None, max_subz=None):
    stdout.write(('%s,%s,%s,%s\n' % ('count', 'date', 'lat', 'lon')).encode())

    date_from = date_from or MIN_DATE
    date_to = date_to or MAX_DATE
    min_zoom = min_zoom or MIN_ZOOM
    max_zoom = max_zoom or MAX_ZOOM
    min_subz = min_subz or min_zoom
    max_subz = max_subz or max_zoom

    assert date_from <= date_to
    assert min_zoom <= max_zoom
    assert min_subz <= max_subz

    tiles = flush(stdout, {}, min_count, max_count)
    start = datetime.datetime.now()
    flush_date = None

    for line in stdin:
        date, z, x, y, count, lat, lon = line.decode().strip().split(',')
        if not date_from <= date <= date_to:
            continue
        count = int(count)
        x = int(x)
        y = int(y)
        z = int(z)
        if not min_zoom <= z <= max_zoom:
            continue

        if flush_date is None:
            start = datetime.datetime.now()
            flush_date = date

        if date != flush_date:
            sys.stderr.write('%s - %s\n' % (flush_date, datetime.datetime.now() - start))
            flush_date = date
            start = datetime.datetime.now()

        if z < min_subz:
            for x, y, z in get_down_tiles(x, y, z, min_subz):
                tiles[(date, z, x, y)] += count
        if z > max_subz:
            x, y, z = get_up_tile(x, y, z, max_subz)
            tiles[(date, z, x, y)] += count
        if min_subz <= z <= max_subz:
            tiles[(date, z, x, y)] += count

    sys.stderr.write('%s - %s\n' % (flush_date, datetime.datetime.now() - start))
    flush(stdout, tiles, min_count, max_count)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Agregate OSM access logs.')
    parser.add_argument('--date_from', default=None)
    parser.add_argument('--date_to', default=None)
    parser.add_argument('--min_zoom', type=int, default=None)
    parser.add_argument('--max_zoom', type=int, default=None)
    parser.add_argument('--min_subz', type=int, default=None)
    parser.add_argument('--max_subz', type=int, default=None)
    parser.add_argument('--min_count', type=int, default=None)
    parser.add_argument('--max_count', type=int, default=None)
    stdin = sys.stdin if sys.version_info.major == 2 else sys.stdin.buffer
    stdout = sys.stdout if sys.version_info.major == 2 else sys.stdout.buffer
    split(stdin, stdout, **parser.parse_args().__dict__)
