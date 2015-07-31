import argparse
import json
import collections
import datetime
import sys

import mercantile
import shapely.geometry


MIN_DATE = '0000-00-00'
MAX_DATE = '9999-99-99'
MIN_ZOOM = 0
MAX_ZOOM = 19

cache_down = {}
cache_up = {}
cache_center = {}
cache_date = {}
cache_in_bound = {}


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


def get_date_precision(date, date_prec, date_prec_measure):
    if date not in cache_date:
        old_date = date
        if date_prec_measure == 'd':
            date = '%s-%02d' % (date[:7], int(date[8:]) // date_prec * date_prec + 1)
        elif date_prec_measure == 'm':
            date = '%s-%02d-01' % (date[:4], int(date[5:7]) // date_prec * date_prec + 1)
        elif date_prec_measure == 'y':
            date = '%04d-01-01' % (int(date[:4]) // date_prec * date_prec + 1)
        else:
            raise TypeError('unknown date precision measure %s' % date_prec_measure)
        cache_date[old_date] = date
        return date
    return cache_date[date]


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


def in_boundaries(lat, lon, boundary, west, south, east, north):
    k = (lat, lon)
    if k not in cache_in_bound:
        in_bounds = lat < north and lat > south and lon > west and lon < east
        if in_bounds:
            in_bounds = boundary.contains(shapely.geometry.Point(lon, lat))
        cache_in_bound[k] = in_bounds
        return in_bounds
    return cache_in_bound[k]


def flush(stdout, tiles, min_count, max_count, boundary):
    boundary_bounds = boundary.bounds
    for k, count in tiles.items():
        if min_count and count < min_count:
            continue
        if max_count and count > max_count:
            continue
        date, z, x, y = k
        lat, lon = calculate_center(x, y, z)
        if boundary is not None:
            if not in_boundaries(lat, lon, boundary, *boundary_bounds):
                continue
        stdout.write(('%s,%s,%s,%s\n' % (count, date, lat, lon)).encode())
    return collections.defaultdict(int)


def split(stdin, stdout, date_precision=None,
          boundary=None, boundary_buffer=None,
          date_from=None, date_to=None,
          min_count=None, max_count=None,
          min_zoom=None, max_zoom=None,
          min_subz=None, max_subz=None):
    stdout.write(('%s,%s,%s,%s\n' % ('count', 'date', 'lat', 'lon')).encode())

    if boundary:
        boundary = shapely.geometry.shape(json.load(open(boundary)))
        if boundary_buffer is not None:
            boundary = boundary.buffer(boundary_buffer)
    if date_precision:
        date_prec = float(date_precision[:-1])
        date_prec_measure = date_precision[-1:]
    date_from = date_from or MIN_DATE
    date_to = date_to or MAX_DATE
    min_zoom = min_zoom or MIN_ZOOM
    max_zoom = max_zoom or MAX_ZOOM
    min_subz = min_subz or min_zoom
    max_subz = max_subz or max_zoom

    assert date_from <= date_to
    assert min_zoom <= max_zoom
    assert min_subz <= max_subz

    tiles = flush(stdout, {}, min_count, max_count, boundary)
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

        if date_precision is not None:
            date = get_date_precision(date, date_prec, date_prec_measure)

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
    flush(stdout, tiles, min_count, max_count, boundary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Agregate OSM access logs.')
    parser.add_argument('--date_from', default=None)
    parser.add_argument('--date_to', default=None)
    parser.add_argument('--date_precision', default=None)
    parser.add_argument('--boundary', default=None)
    parser.add_argument('--boundary_buffer', type=float, default=None)
    parser.add_argument('--min_zoom', type=int, default=None)
    parser.add_argument('--max_zoom', type=int, default=None)
    parser.add_argument('--min_subz', type=int, default=None)
    parser.add_argument('--max_subz', type=int, default=None)
    parser.add_argument('--min_count', type=int, default=None)
    parser.add_argument('--max_count', type=int, default=None)
    stdin = sys.stdin if sys.version_info.major == 2 else sys.stdin.buffer
    stdout = sys.stdout if sys.version_info.major == 2 else sys.stdout.buffer
    split(stdin, stdout, **parser.parse_args().__dict__)
