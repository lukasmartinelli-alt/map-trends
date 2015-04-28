#!/bin/bash
for filename in ls tile_logs/tiles-2015-01-0*; do
    echo $(basename $filename)
    cat $filename | pypy convert.py > tiles_csv/$(basename "$filename" .csv)
done
