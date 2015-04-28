# map-trends
Show trends on maps

## Prepare Data

1. Download all logs from the server.

```bash
wget -m http://planet.openstreetmap.org/tile_logs
```

2. Extract logs

```bash
unxz *.xz
```

3. Convert logs to CSV (`1/2/3 123` to `1 2 3 123`).
```bash
sed -i 's/\// /g' *.txt
```

- [ ] Convert tile indizes to latitude and longitude
