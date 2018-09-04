#!/bin/bash

set -e

DATA_PATH=./data
DOWNLOAD_PATH=$DATA_PATH/download
LOG_PATH=$DATA_PATH/log
OUTPUT_PATH=$DATA_PATH/output
LINKS_PATH=$OUTPUT_PATH/filiacao-links.csv
FILIACAO_PATH=$OUTPUT_PATH/filiacao.csv

rm -rf $DOWNLOAD_PATH/filiacao-* $LINKS_PATH
mkdir -p $DOWNLOAD_PATH $OUTPUT_PATH $LOG_PATH

time scrapy runspider \
	--loglevel=INFO \
	--logfile=$LOG_PATH/filiacao-download.log \
	-o $LINKS_PATH \
	filiacao_download.py
time scrapy runspider \
	--loglevel=INFO \
	--logfile=$LOG_PATH/filiacao-parse.log \
	-o $FILIACAO_PATH \
	filiacao_parse.py

time xz -4z $LINKS_PATH
time xz -4z $FILIACAO_PATH
