#!/bin/bash

set -e

DATA_PATH=./data
OUTPUT_PATH=$DATA_PATH/output

rm -rf $OUTPUT_PATH
mkdir -p $OUTPUT_PATH

OPTS=""
if [ "$1" = "--use-mirror" ]; then
	OPTS="$1"
fi

time python tse.py headers

time python tse.py $OPTS candidatura
time python tse.py $OPTS bem-declarado
time python tse.py $OPTS receita
time python tse.py $OPTS despesa
time python tse.py $OPTS votacao-zona
