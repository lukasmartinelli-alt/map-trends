#!/usr/bin/env bash
set -e

function download_test_log() {
    wget http://planet.openstreetmap.org/tile_logs/tiles-2015-01-01.txt.xz
}

function download_logs() {
    wget -r -l1 -N --no-parent http://planet.openstreetmap.org/tile_logs
}

function decompress() {
    cd tile_logs
    parallel 'unxz {}' ::: *.xz
    rm *.xz
    cd ..
}

function prepare_logs() {
    cd tile_logs
    sed -i 's/\// /g' *.txt
    rename txt csv *.txt
    cd ..
}

function convert_coords() {
    mkdir -p tile_coords
    header="z x y requests latitude longitude"
    for filename in $(ls tile_logs/*.csv); do
        echo $(basename $filename)
        echo "$header" > tile_coords/$(basename "$filename")
        cat $filename | ./calc_coords.py >> tiles_coords/$(basename "$filename")
    done
}

function prepare_mapbox() {
    mkdir -p tile_mapbox
    for filename in $(ls tile_coords/*.csv); do
        cat $filename | tr ' ' ',' > tile_mapbox/$(basename "$filename").mapbox.csv
    done
}

if [ "$1" = "download" ]; then
    # download_test_log
    download_logs
    mv planet.openstreetmap.org/tile_logs tile_logs && rm -r planet.openstreetmap.org
fi

if [ "$1" = "prepare" ]; then
    prepare_logs
fi

if [ "$1" = "convert" ]; then
   convert_coords
fi

if [ "$1" = "decompress" ]; then
   decompress 
fi

if [ "$1" = "mapbox" ]; then
   prepare_mapbox
fi
