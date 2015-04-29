#!/usr/bin/env bash
set -e

function download_test_log() {
    mkdir -p tile_logs && cd tile_logs
    wget http://planet.openstreetmap.org/tile_logs/tiles-2015-01-01.txt.xz
    cd ..
}

function download_logs() {
    wget -nv -nc -nH -A xz -m http://planet.openstreetmap.org/tile_logs
}

function prepare_logs() {
    cd tile_logs
    unxz *.xz
    rm *.xz
    sed -i 's/\// /g' *.txt
    rename txt csv *.txt
    cd ..
}

function convert_coords() {
    mkdir -p tile_coords
    for filename in $(ls tile_logs/*.csv); do
    echo $(basename $filename)
    echo "z x y requests latitude longitude" > tile_coords/$(basename "$filename")
    cat $filename | ./calc_coords.py >> tiles_coords/$(basename "$filename")
    done
}

function prepare_mapbox() {
    mkdir -p tile_mapbox
    for filename in $(ls tile_coords/*.csv); do
    cat $filename | tr ' ' ',' > tile_mapbox/$(basename "$filename").mapbox.csv
    done
}

if [ "$1" -eq "test" ]; then
    download_test_log
else
    download_logs
fi

prepare_logs
convert_coords
prepare_mapbox
