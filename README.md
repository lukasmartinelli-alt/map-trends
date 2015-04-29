# map-trends

Show trends on maps as part of a term paper.

- [ ] Formulate project proposal
- [ ] Define scope of project

## Install

Requirements

- OSX or Linux
- Python 2.7, Python 3.4 or PyPy

Install Python requirements.

```
pip install -r requirements.txt
```

## Prepare Data

You have several possiblities to prepare the data:

- Follow the instructions
- Use `./prepare.sh`
- Download prepared tiles directly

### Download, Extract and Transform

Download all logs from the server.

```bash
wget -nH -A xz -m http://planet.openstreetmap.org/tile_logs
```

Extract logs and remove compressed versions.

```bash
unxz *.xz
rm *.xz
```

Expand tile coordinates in CSV to separate columns (from `1/2/3 123` to `1 2 3 123`).

```bash
sed -i 's/\// /g' *.txt
```

Rename `.txt` files to `.csv`.

```bash
rename txt csv *.txt
```

### Calculate Coordinates

Convert tile indizes from the logs with [slippy tile names](https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames) to [Spherical Mercator](http://docs.openlayers.org/library/spherical_mercator.html) coordinates add CSV header.

```bash
mkdir -p tile_coords

for filename in $(ls tile_logs/*.csv); do
  echo $(basename $filename)
  echo "z x y requests latitude longitude" > tile_coords/$(basename "$filename")
  cat $filename | ./calc_coords.py >> tiles_coords/$(basename "$filename")
done
```

Convert from space delimited to comma delimited CSV (requirements for use in Mapbox).

```bash
mkdir -p tile_mapbox

for filename in $(ls tile_coords/*.csv); do
  cat $filename | tr ' ' ',' > tile_mapbox/$(basename "$filename").mapbox.csv
done
```
