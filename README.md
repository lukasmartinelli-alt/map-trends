# map-trends

Show trends on maps

## Install

Requirements

- OSX or Linux
- Python 2.7, Python 3.4 or PyPy

Install Python requirements.

```
pip install -r requirements.txt
```

## Prepare Data

### Download, Extract and Transform

Download all logs from the server.

```bash
mkdir -p tile_logs && cd tile_logs
wget -nH --cut-dirs -A xz -m http://planet.openstreetmap.org/tile_logs
```

Extract logs and remove compressed versions.

```bash
unxz *.xz && rm *.xz
```

Expand tile coordinates in CSV to separate columns (from `1/2/3 123` to `1 2 3 123`).

```bash
sed -i 's/\// /g' *.txt
```

Rename `.txt` files to `.csv`.

```bash
for filename in ls tile_logs/*.txt; do
  mv $filename $(basename "$filename".csv)
done
```

### Calculate Coordinates

Convert tile indizes from the logs with [slippy tile names](https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames) to [Spherical Mercator](http://docs.openlayers.org/library/spherical_mercator.html) coordinates add CSV header.

```bash
mkdir -p tile_coordinates

for filename in ls tile_logs/*.csv; do
  echo $(basename $filename)
  echo "z x y requests latitude longitude" > tile_coordinates/$(basename "$filename")
  cat $filename | ./calc_coordinates.py >> tiles_csv/$(basename "$filename".csv)
done
```

Convert from space delimited to comma delimited CSV (requirements for use in Mapbox).

```bash
for filename in ls tile_logs/*.csv; do
  cat $filename | tr ' ' ',' > "$filename".mapbox.csv
done
```
