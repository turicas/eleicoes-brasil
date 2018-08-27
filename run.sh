#!/bin/bash

set -e

DATA_PATH=./data
OUTPUT_PATH=$DATA_PATH/output

rm -rf $OUTPUT_PATH
mkdir -p $OUTPUT_PATH

time python tse.py headers
time python tse.py candidatura \
	--years=all --output=$OUTPUT_PATH/candidatura.csv.gz
time python tse.py bemdeclarado \
	--years=all --output=$OUTPUT_PATH/bemdeclarado.csv.gz
time python tse.py votacao-zona \
	--years=all --output=$OUTPUT_PATH/votacao-zona.csv.gz
time rows csv2sqlite \
	--schemas=headers/schema-candidatura.csv,headers/schema-bemdeclarado.csv,headers/schema-votacao-zona.csv \
	$OUTPUT_PATH/candidatura.csv.gz \
	$OUTPUT_PATH/bemdeclarado.csv.gz \
	$OUTPUT_PATH/votacao-zona.csv.gz \
	$DATA_PATH/eleicoes-brasil.sqlite
