#!/bin/bash

set -e

DATA_PATH=./data
OUTPUT_PATH=$DATA_PATH/output

rm -rf $OUTPUT_PATH
mkdir -p $OUTPUT_PATH

time python tse.py headers

time python tse.py candidatura
time python tse.py bem-declarado
time python tse.py votacao-zona
time python tse.py receita
time python tse.py despesa
