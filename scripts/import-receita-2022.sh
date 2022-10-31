#!/bin/bash

set -e

URL="https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip"
DOWNLOAD_FILENAME="data/download/prestacao_de_contas_eleitorais_candidatos_2022.zip"

mkdir -p $(dirname $DOWNLOAD_FILENAME)
rm -rf "$DOWNLOAD_FILENAME" $(dirname $DOWNLOAD_FILENAME)/receitas_* $(dirname $DOWNLOAD_FILENAME)/despesas_* $(dirname $DOWNLOAD_FILENAME)/leiame*
wget --user-agent="Mozilla/4" -O "$DOWNLOAD_FILENAME" -c -t 0 $URL
cd $(dirname $DOWNLOAD_FILENAME)
unzip "$(basename $DOWNLOAD_FILENAME)"
cd -

echo "DROP TABLE IF EXISTS receita_2022" | psql $DATABASE_URL
rows pgimport \
	--dialect=excel-semicolon \
	--input-encoding=latin1 \
	--schema=:text: \
	data/download/receitas_candidatos_2022_BRASIL.csv \
	$DATABASE_URL \
	receita_2022

echo "DROP TABLE IF EXISTS receita_2022_doador_originario" | psql $DATABASE_URL
rows pgimport \
	--dialect=excel-semicolon \
	--input-encoding=latin1 \
	--schema=:text: \
	data/download/receitas_candidatos_doador_originario_2022_BRASIL.csv \
	$DATABASE_URL \
	receita_2022_doador_originario
