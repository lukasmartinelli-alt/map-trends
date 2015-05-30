import argparse
import collections
import csv
import datetime
import gzip
import io
import json
import lzma
import os
import pickle
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import lxml.etree
import mercantile
import shapely.geometry
import shapely.wkt
import overpass
import shapely.geometry
import shapely.wkt


LOGS_URL = 'http://planet.openstreetmap.org/tile_logs/'
MIN_DATE = '0000-00-00'
MAX_DATE = '9999-99-99'
EXT = '.txt.xz'

COUNTRIES_QUERY = ('[out:csv(::id, "ISO3166-1", "ISO3166-1:alpha2")];'
                   '('
                   'relation["ISO3166-1"];'
                   'relation["ISO3166-1:alpha2"];'
                   ');'
                   'out tags;')
RELATION_QUERY = ('[out:csv(::id, "ISO3166-1", "ISO3166-1:alpha2")];'
                  '('
                  'relation(%s);'
                  ');'
                  'out tags;')

PREFETCH_GEOMETRY_LINK = 'http://polygons.openstreetmap.fr/?id=%s'
FETCH_GEOMETRY_LINK = 'http://polygons.openstreetmap.fr/get_wkt.py?id=%s&params=0'
MAX_FETCH_ATTEMPTS = [1, 3, 10, 30]
COUNTRIES_IDS_SKIP = (
    11980,
    1111111,
    1362232,
    1401925,
)

MIN_ZOOM = 0
MAX_ZOOM = 19
SPLIT_ZOOM = 8
NOT_COUNTRY_PART_STEP = 10

DUMPS_CACHE_FOLDER = 'tile_logs'
COUNTRIES_GEOM_CACHE_FOLDER = 'countries'
GEOM_CACHE = 'cache_geoms.picle'
PREPROCESSED_GEOM_CACHE = 'cache_preprocessed.picle'
SPLITED_GEOM_CACHE = 'cache_splited.picle'
TILE_CACHE = 'cache_tile.json'


class Stat(object):

    def __init__(self):
        self.out = sys.stderr
        self.start = datetime.datetime.now()
        self.in_all = 0
        self.in_no_cached = 0
        self.in_child_cache = 0
        self.in_direct_cache = 0
        self.child_zoom_less = 0
        self.child_zoom_equal = 0
        self.filtered_bbox = 0
        self.filtered_geom = 0
        self.append_geom = 0

    def log_stats(self, msg, cache):
        cached_for_child = 0
        for cached_item in cache.values():
            if '|' not in cached_item:
                cached_for_child += 1
        self.log('%s - %s - ps: %s/%s - cc: %s/%s - zm: %s/%s - '
                 'fl: %s/%s - ap: %s - cs: %s/%s',
                 msg, datetime.datetime.now() - self.start,
                 self.in_all, self.in_no_cached,
                 self.in_child_cache, self.in_direct_cache,
                 self.child_zoom_less, self.child_zoom_equal,
                 self.filtered_bbox, self.filtered_geom,
                 self.append_geom,
                 cached_for_child, len(cache),
                 )

    def log(self, msg, *args):
        self.out.write('%s\n' % (msg % args))


def _fetch(link):
    attempt = 0
    while True:
        try:
            time.sleep(MAX_FETCH_ATTEMPTS[attempt])
            request = urllib.request.Request(link, headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            })
            return gzip.open(urllib.request.urlopen(request)).read().decode()
        except urllib.error.HTTPError:
            attempt += 1
            if attempt >= len(MAX_FETCH_ATTEMPTS):
                raise


def get_country_geom(osm_id, iso):
    prefetch_link = FETCH_GEOMETRY_LINK % osm_id
    link = FETCH_GEOMETRY_LINK % osm_id

    if not os.path.exists(COUNTRIES_GEOM_CACHE_FOLDER):
        os.mkdir(COUNTRIES_GEOM_CACHE_FOLDER)
    file_name_wkt = os.path.join(COUNTRIES_GEOM_CACHE_FOLDER,
                                 '%s-%s.wkt' % (iso, osm_id))
    file_name_geojson = os.path.join(COUNTRIES_GEOM_CACHE_FOLDER,
                                     '%s-%s.geojson' % (iso, osm_id))
    if os.path.exists(file_name_wkt):
        with open(file_name_wkt, 'r') as file:
            response = file.read()
        geom = shapely.wkt.loads(response)
    elif os.path.exists(file_name_geojson):
        with open(file_name_geojson, 'r') as file:
            response = file.read()
        geom = shapely.geometry.shape(json.loads(response))
    else:
        _fetch(prefetch_link)
        response = _fetch(link)
        geom = shapely.wkt.loads(response)
        with open(file_name_wkt, 'w') as file:
            file.write(response)

    return geom


def get_countries(rel=None, country=None):
    countries = {}
    if rel:
        query = RELATION_QUERY % rel
    else:
        query = COUNTRIES_QUERY
    response = overpass.API()._GetFromOverpass(query)
    reader = csv.reader(io.StringIO(response), delimiter='\t',)
    next(reader)
    for osm_id, iso3166_1, iso3166_1_alpha2 in reader:
        osm_id = int(osm_id)
        iso = iso3166_1 or iso3166_1_alpha2
        if not rel and not country and osm_id in COUNTRIES_IDS_SKIP:
            continue
        if not rel and (not iso or len(iso) != 2):
            continue
        if country and iso != country:
            continue
        if (osm_id, iso) in countries:
            continue
        Stat().log('%s-%s', iso, osm_id)
        geom = get_country_geom(osm_id, iso)
        countries[osm_id] = (iso, geom, geom.bounds)

    return countries


def _clear_xml_element(element):
    element.clear()
    for ancestor in element.xpath('ancestor-or-self::*'):
        while ancestor.getprevious() is not None:
            del ancestor.getparent()[0]


def get_date_from_link(link):
    return link[:-len(EXT)][-len(MIN_DATE):]


def get_tile_usage_dump_links(date_from=None, date_to=None):
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


def get_tile_usage_dump(link):
    dump_cache = os.path.join(DUMPS_CACHE_FOLDER,
                              link[-len('tiles-YYYY-MM-DD.txt.xz'):])
    if os.path.exists(dump_cache):
        return io.BytesIO(open(dump_cache, 'rb').read())
    return urllib.request.urlopen(link)


def detect_country(b, x, y, z, part_zoom, part_countries, all_countries, stat):
    twest, tsouth, teast, tnorth = b
    tgeom = shapely.geometry.box(twest, tsouth, teast, tnorth)
    result = None

    if z < part_zoom:
        countries = all_countries
    else:
        delta_zooms = z - part_zoom
        delta = 2 ** delta_zooms
        px = x // delta
        py = y // delta
        countries = part_countries['%s/%s/%s' % (part_zoom, px, py)]

    for iso, boundary, outer_box in countries:
        owest, osouth, oeast, onorth = outer_box
        if not (twest <= oeast and teast >= owest and
                tnorth >= osouth and tsouth <= onorth):
            stat.filtered_bbox += 1
            continue
        if not boundary.intersects(tgeom):
            stat.filtered_geom += 1
            continue
        if result is None:
            result = {iso}
        else:
            result.add(iso)
        stat.append_geom += 1
    return result and '|'.join(sorted(result)) or '??'


def detect_country_with_cache(k, b, x, y, z,
                              part_zoom, part_countries, all_countries,
                              min_cache_zoom, cache, stat):
    stat.in_all += 1
    if k in cache:
        stat.in_direct_cache += 1
        return cache[k]

    for pz in range(min_cache_zoom, z):
        delta_zooms = z - pz
        delta = 2 ** delta_zooms
        px = x // delta
        py = y // delta
        ck = '%s/%s/%s' % (pz, px, py)
        potential_cc = False
        if ck in cache:
            country = cache[ck]
            potential_cc = True
        else:
            stat.in_no_cached += 1
            country = detect_country(
                b, px, py, pz, part_zoom, part_countries, all_countries, stat)
            cache[k] = country

        if pz < z and '|' not in country:
            stat.child_zoom_less += 1
            if potential_cc:
                stat.in_child_cache += 1
            return country

    stat.in_no_cached += 1
    stat.child_zoom_equal += 1
    country = detect_country(
        b, x, y, z, part_zoom, part_countries, all_countries, stat)
    cache[k] = country
    return country


def process_item(out, min_cache_zoom, cache, link,
                 part_zoom, part_countries, all_countries,
                 min_zoom, max_zoom, remove_non_box):
    stat = Stat()
    date = get_date_from_link(link)

    for line in lzma.LZMAFile(get_tile_usage_dump(link)):
        path, count = line.decode().strip().split()
        z, x, y = path.split('/')

        x = int(x)
        y = int(y)
        z = int(z)

        if min_zoom is not None and z < min_zoom:
            continue
        if max_zoom is not None and z > max_zoom:
            continue

        twest, tsouth, teast, tnorth = b = mercantile.bounds(x, y, z)
        country = detect_country_with_cache(
            path, b, x, y, z, part_zoom, part_countries, all_countries,
            min_cache_zoom, cache, stat)

        if remove_non_box and country == '??':
            continue

        lat = tnorth + (tnorth - tsouth) / 2
        lon = twest + (teast - twest) / 2

        out.write(('%s,%s,%s,%s,%s,%s,%s,%s\n' % (
            date, z, x, y, count, lat, lon, country)).encode())
    stat.log_stats(date, cache)


def create_cache(part_zoom, countries, splited_countries, min_cache_zoom):
    stat = Stat()

    cache = {}
    if min_cache_zoom:
        stat.log_stats('cache (%s)' % min_cache_zoom, cache)
        return min_cache_zoom, cache

    min_cache_zoom = MIN_ZOOM
    for z in range(MAX_ZOOM + 1):
        for x in range(2 ** z):
            for y in range(2 ** z):
                k = '%s/%s/%s' % (z, x, y)
                b = mercantile.bounds(x, y, z)
                country = detect_country_with_cache(
                    k, b, x, y, z, part_zoom, countries, splited_countries,
                    z, cache, stat)
                if '|' not in country:
                    min_cache_zoom = z
        if min_cache_zoom > 0:
            break
    stat.log_stats('cache (%s)' % min_cache_zoom, cache)
    return min_cache_zoom, cache


def filter_geoms(x, y, z, countries):
    twest, tsouth, teast, tnorth = mercantile.bounds(x, y, z)
    box = shapely.geometry.box(twest, tsouth, teast, tnorth)
    filtered_countries = []
    for iso, geom, geom_box in countries:
        gwest, gsouth, geast, gnorth = geom_box
        if not (twest <= geast and teast >= gwest and
                tnorth >= gsouth and tsouth <= gnorth):
            continue
        if not geom.intersects(box):
            continue
        geom = geom.intersection(box)
        filtered_countries.append((iso, geom, geom.bounds))
    Stat().log('polygons in %s/%s/%s: %s', z, x, y, len(filtered_countries))
    return '%s/%s/%s' % (z, x, y), tuple(filtered_countries)


def preprocess_countries(countries, remove_non_box):
    grouped_countries = collections.defaultdict(list)
    for iso, geom, bbox in countries.values():
        grouped_countries[iso].append(geom)
    Stat().log('grouped %s', len(grouped_countries))

    step = NOT_COUNTRY_PART_STEP
    negs = [[shapely.geometry.box(lat, lon, lat + step, lon + step)]
            for lat in range(-180, 180, step)
            for lon in range(-90, 90, step)]

    splited_countries = []
    for index, item in enumerate(grouped_countries.items()):
        iso, geoms = item
        geom = None
        for geom_other in geoms:
            if geom is None:
                geom = geom_other.buffer(0)
            else:
                geom = geom.union(geom_other.buffer(0))

        for j, neg in enumerate(negs):
            if neg[0] is None or not neg[0].intersects(geom):
                continue
            neg[0] = neg[0].difference(geom)
            if neg[0].is_empty:
                neg[0] = None

        so = 0
        sb = 0
        go = geom.area
        gb = shapely.geometry.box(*geom.bounds).area
        for subgeom in getattr(geom, 'geoms', [geom]):
            so += subgeom.area
            sb += shapely.geometry.box(*subgeom.bounds).area
            outer_box = subgeom.bounds
            splited_countries.append((iso, geom, outer_box))

        Stat().log('{:03d} {} {:7.2f}: {:3.0f} {:8.2f} => {:7.2f}'.format(
            index, iso, go, sb / gb * 100, gb, sb))

    if remove_non_box:
        for neg in (neg for neg in negs if neg[0] is not None):
            for iso, geom, box in splited_countries:
                if shapely.geometry.box(*box).intersects(shapely.geometry.box(*neg[0].bounds)):
                    break
            else:
                neg[0] = None

    for neg in (neg for neg in negs if neg[0] is not None):
        splited_countries.append(('??', neg[0], neg[0].bounds))

    return splited_countries


def process_all(out, date_from=None, date_to=None,
                min_zoom=None, max_zoom=None,
                rel=None, country=None, min_cache_zoom=None):
    if not rel and not country and os.path.exists(GEOM_CACHE):
        full_countries = pickle.load(open(GEOM_CACHE, 'rb'))
    else:
        full_countries = get_countries(rel, country)
        if not rel and not country:
            pickle.dump(full_countries, open(GEOM_CACHE, 'wb'))
    Stat().log('total countries: %s', len(full_countries))

    if not rel and not country and os.path.exists(PREPROCESSED_GEOM_CACHE):
        splited_countries = pickle.load(open(PREPROCESSED_GEOM_CACHE, 'rb'))
    else:
        splited_countries = preprocess_countries(full_countries,
                                                 rel or country)
        if not rel and not country:
            pickle.dump(splited_countries, open(PREPROCESSED_GEOM_CACHE, 'wb'))
    Stat().log('total polygons: %s', len(splited_countries))

    if not rel and not country and os.path.exists(SPLITED_GEOM_CACHE):
        part_zoom, part_countries = pickle.load(open(SPLITED_GEOM_CACHE, 'rb'))
    else:
        part_zoom = SPLIT_ZOOM
        part_countries = dict(filter_geoms(x, y, part_zoom, splited_countries)
                              for x in range(2 ** part_zoom)
                              for y in range(2 ** part_zoom))
        if not rel and not country:
            pickle.dump([part_zoom, part_countries], open(SPLITED_GEOM_CACHE, 'wb'))
    Stat().log('total parts: %s', len(part_countries))

    if not rel and not country and os.path.exists(TILE_CACHE):
        min_cache_zoom, cache = json.load(open(TILE_CACHE))
    else:
        min_cache_zoom, cache = create_cache(
            part_zoom, part_countries, splited_countries, min_cache_zoom)

    for link in get_tile_usage_dump_links(date_from, date_to):
        process_item(out, min_cache_zoom, cache, link,
                     part_zoom, part_countries, splited_countries,
                     min_zoom, max_zoom, rel or country)
    if not rel and not country:
        json.dump([min_cache_zoom, cache], open(TILE_CACHE, 'w'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch and concat OSM access logs.')
    parser.add_argument('--date_from', default=None)
    parser.add_argument('--date_to', default=None)
    parser.add_argument('--min_zoom', type=int, default=None)
    parser.add_argument('--max_zoom', type=int, default=None)
    parser.add_argument('--rel', type=int, default=None)
    parser.add_argument('--country', default=None)
    parser.add_argument('--min_cache_zoom', type=int, default=None)
    stdout = sys.stdout if sys.version_info.major == 2 else sys.stdout.buffer
    process_all(stdout, **parser.parse_args().__dict__)
