#!/bin/bash

set -e

DATA_PATH=./data
OUTPUT_PATH=$DATA_PATH/output
SQLITE_PATH=$DATA_PATH/eleicoes-brasil.sqlite

rm -rf $SQLITE_PATH

for table in candidatura bem-declarado votacao-zona receita despesa; do
	time rows csv-to-sqlite \
		--schemas=headers/schema-$table.csv \
		$OUTPUT_PATH/$table.csv.gz $SQLITE_PATH
done
