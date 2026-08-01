#!/bin/bash

# LEGADO: este pipeline dependia dos ZIPs em agencia.tse.jus.br, que não são mais publicados nesse endereço. Não o use
# para obter filiações atuais. O scraper vigente é `filiacao.py`, que consulta a API filia2-consulta do TSE.

set -e

DATA_PATH=./data
DOWNLOAD_PATH=$DATA_PATH/download
LOG_PATH=$DATA_PATH/log
OUTPUT_PATH=$DATA_PATH/output
LINKS_PATH=$OUTPUT_PATH/filiacao-links.csv
FILIACAO_PATH=$OUTPUT_PATH/filiacao.csv

rm -rf $DOWNLOAD_PATH/filiacao* $LINKS_PATH $OUTPUT_PATH/filiacao*
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

gzip $LINKS_PATH
gzip $FILIACAO_PATH
