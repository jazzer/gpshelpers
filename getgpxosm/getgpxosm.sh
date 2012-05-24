#/bin/bash

file=$1

grep '<url>' $file | perl -pne 's/^.*url>\D*(\d+)<\/url.*$/http:\/\/www.openstreetmap.org\/trace\/\1\/data/' | xargs -n1 wget -O "track.gpx"
