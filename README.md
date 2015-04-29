# map-trends
Show trends on maps

## Prepare Data

Download all logs from the server to the current directory.

```bash
wget -nH --cut-dirs -A xz -m http://planet.openstreetmap.org/tile_logs

```

Extract logs and remove compressed versions

```bash
unxz *.xz && rm *.xz
```

Convert logs to space delimited CSV (`1/2/3 123` to `1 2 3 123`).

```bash
sed -i 's/\// /g' *.txt
```

Convert tile indizes from logs to longitude and latitude and add CSV header

```bash
for filename in ls tile_logs/*.txt; do
  echo $(basename $filename)
  echo "z x y requests latitude longitude" > tiles_csv/$(basename "$filename" .csv)
  cat $filename | pypy convert.py >> tiles_csv/$(basename "$filename" .csv)
done
```

Convert from space delimited to comma delimited CSV (Mapbox requires that)

```bash
cat tiles-2015-01-01.csv | tr ' ' ',' > tiles-2015-01-01.mapbox.csv
```
