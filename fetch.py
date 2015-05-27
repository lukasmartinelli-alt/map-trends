import argparse
import datetime
import json
import lzma
import urllib.parse
import urllib.request
import sys

import lxml.etree
import mercantile
import shapely.geometry


LOGS_URL = 'http://planet.openstreetmap.org/tile_logs/'
MIN_DATE = '0000-00-00'
MAX_DATE = '9999-99-99'
EXT = '.txt.xz'


class CacheItemPos(object):

    in_bound = True

    __slots__ = ('lat', 'lon')

    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon


class CacheItemNeg(object):

    in_bound = False

    __slots__ = ('lat', 'lon')

    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon


def _clear_xml_element(element):
    element.clear()
    for ancestor in element.xpath('ancestor-or-self::*'):
        while ancestor.getprevious() is not None:
            del ancestor.getparent()[0]


def get_date_from_link(link):
    return link[:-len(EXT)][-len(MIN_DATE):]


def calculate_center(x, y, zoom):
    bounds = mercantile.bounds(x, y, zoom)
    height = bounds.north - bounds.south
    width = bounds.east - bounds.west
    center = (bounds.north + height / 2, bounds.west + width / 2)
    return center


def in_boundaries(lat, lon, boundary, west, south, east, north):
    in_bounds = lat < north and lat > south and lon > west and lon < east
    if not in_bounds:
        return False
    return boundary.contains(shapely.geometry.Point(lon, lat))


def get_links(date_from=None, date_to=None):
    date_from = date_from or MIN_DATE
    date_to = date_to or MAX_DATE
    links = set()

    response = urllib.request.urlopen(LOGS_URL)
    for action, element in lxml.etree.iterparse(response, tag='a', html=True):
        link = element.attrib['href']
        _clear_xml_element(element)
        if not link.endswith(EXT):
            continue
        if not date_from <= get_date_from_link(link) <= date_to:
            continue
        links.add(urllib.parse.urljoin(LOGS_URL, link))

    return sorted(links)


def process_item(out, _cache, link, boundary):
    start = datetime.datetime.now()
    tiles = 0
    tiles_no_cached = 0
    date = get_date_from_link(link)
    if boundary:
        boundary_bounds = boundary.bounds

    response = urllib.request.urlopen(link)
    for line in lzma.LZMAFile(response):
        path, count = line.strip().split()
        count = count.decode()
        zoom, x, y = path.decode().split('/')
        tiles += 1
        if path not in _cache:
            tiles_no_cached += 1
            lat, lon = calculate_center(int(x), int(y), int(zoom))
            if boundary:
                in_bound = in_boundaries(lat, lon, boundary, *boundary_bounds)
            else:
                in_bound = True
            _cache[path] = (CacheItemPos if in_bound else CacheItemNeg)(lat, lon)
        cache_item = _cache[path]
        if not cache_item.in_bound:
            continue
        out.write(('%s,%s,%s,%s,%s,%s,%s\n' % (
            date, zoom, x, y, count, cache_item.lat, cache_item.lon)).encode())
    sys.stderr.write('%s - %s - %s/%s\n' % (
        link, datetime.datetime.now() - start, tiles_no_cached, tiles))


def process_all(out, date_from=None, date_to=None, boundary=None):
    if boundary is not None:
        boundary = shapely.geometry.shape(json.load(open(boundary)))

    _cache = {}

    for link in get_links(date_from, date_to):
        process_item(out, _cache, link,  boundary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch and concat OSM access logs.')
    parser.add_argument('--date_from', default=None)
    parser.add_argument('--date_to', default=None)
    parser.add_argument('--boundary', default=None)
    stdout = sys.stdout if sys.version_info.major == 2 else sys.stdout.buffer
    process_all(stdout, **parser.parse_args().__dict__)
