#!/usr/bin/env bats
source prepare.sh

download_test_log
prepare_logs

@test "Check format of prepared file" {
    first_line=$(head -n 1 tile_logs/tiles-2015-01-01.csv)
    second_line=$(cat tile_logs/tiles-2015-01-01.csv | sed -n 2p)
    echo $first_line
    echo $second_line

    [ $first_line= "z x y requests latitude longitude" ]
    [ $second_line = "0 0 0 497516 170.1022575596132 0.0" ]
}
