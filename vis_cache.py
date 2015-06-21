import json
import itertools
import collections

import mercantile
import shapely.geometry


color = itertools.cycle([
    '#%X%X%X' % (r, g, b)
    for r in range(14, 4, -1)
    for g in range(14, 4, -1)
    for b in range(14, 4, -1)
    if 20 < r + g + b < 36
])


def get_color():
    for i in range(3):
        r = next(color)
    return r


color_map = collections.defaultdict(get_color)
color_map.update({
    '??': '#00F',
    'AQ': '#000',
})
duplicates = {
    # 'EH|MA',
    # 'FR|FX',
    # 'FR|GF',
    # 'NO|SJ',
    # 'RU|UA',
}


def tile_to_rect(zoom, x, y, v):
    zoom = int(zoom)
    x = int(x)
    y = int(y)
    box = mercantile.bounds(x, y, zoom)
    return {
        'type': 'Feature',
        'properties': {
            't': '%s/%s/%s' % (zoom, x, y),
            'c': v,
            'k': color_map[v]
        },
        'geometry': shapely.geometry.mapping(shapely.geometry.box(*box)),
    }


def generate_geojson(zoom):
    cache = json.load(open('cache_tile.json'))
    cache_trim = [tile_to_rect(*k.split('/'), v=v)
                  for k, v in cache[1].items()
                  if int(k.split('/')[0]) <= zoom
                  and (len(v.split('|')) == 1 or (v in duplicates and int(k.split('/')[0]) == zoom))]
    cache_trim = {
        'type': 'FeatureCollection',
        'features': cache_trim,
    }
    json.dump(cache_trim, open('cache_tile_%s.geojson' % zoom, 'w'), ensure_ascii=False, sort_keys=True)


if __name__ == '__main__':
    generate_geojson(9)
