#!/bin/bash
# Script utilizado para preencher o campo `cpf` na tabela de candidaturas para 2024 com os dados de CPF das
# candidaturas de anos anteriores e os dados de filiação partidária (que contém título eleitoral e CPF) coletados do
# sistema disponibilizado pelo TSE em 2024.
#
# Atenção: o arquivo `data/Filiacao.csv` gerado pelo scraper de filiação partidária é muito grande e, por isso, pode
# é necessário simplificá-lo para rodar nesse script. Use o comando:
#     python scripts/simplifica_filiacao.py data/Filiacao.csv data/output/filiacao_partidaria.csv.gz
#
# Além disso, pode ser útil juntar mais de um arquivo resultante desse processo, dado que o scraping pode retornar
# resultados diferentes em execuções feitas em dias diferentes (e nem sempre a última execução terá todos os dados da
# anterior). Para isso, execute os comandos:
#     python scripts/simplifica_filiacao.py data/2024-08-16-Filiacao.csv.gz data/output/filiacao_partidaria_1.csv.gz
#     python scripts/simplifica_filiacao.py data/2024-09-22-Filiacao.csv.gz data/output/filiacao_partidaria_2.csv.gz
#     python scripts/simplifica_filiacao.py data/2024-09-29-Filiacao.csv.gz data/output/filiacao_partidaria_3.csv.gz
#     python scripts/simplifica_filiacao.py data/2024-12-10-Filiacao.csv.gz data/output/filiacao_partidaria_4.csv.gz
#     echo 'DROP TABLE IF EXISTS filiacao_1' | psql --no-psqlrc "$DATABASE_URL"
#     echo 'DROP TABLE IF EXISTS filiacao_2' | psql --no-psqlrc "$DATABASE_URL"
#     echo 'DROP TABLE IF EXISTS filiacao_3' | psql --no-psqlrc "$DATABASE_URL"
#     echo 'DROP TABLE IF EXISTS filiacao_4' | psql --no-psqlrc "$DATABASE_URL"
#     rows pgimport -s :text: -e utf-8 -d excel data/output/filiacao_partidaria_1.csv.gz "$DATABASE_URL" filiacao_1
#     rows pgimport -s :text: -e utf-8 -d excel data/output/filiacao_partidaria_2.csv.gz "$DATABASE_URL" filiacao_2
#     rows pgimport -s :text: -e utf-8 -d excel data/output/filiacao_partidaria_3.csv.gz "$DATABASE_URL" filiacao_3
#     rows pgimport -s :text: -e utf-8 -d excel data/output/filiacao_partidaria_4.csv.gz "$DATABASE_URL" filiacao_4
#     cat > /tmp/filiacao.sql <<'EOL'
#     SELECT DISTINCT * FROM (
#       SELECT titulo_eleitor, cpf, situacao_eleitor, data_filiacao, nome FROM filiacao_1
#       UNION
#       SELECT titulo_eleitor, cpf, situacao_eleitor, data_filiacao, nome FROM filiacao_2
#       UNION
#       SELECT titulo_eleitor, cpf, situacao_eleitor, data_filiacao, nome FROM filiacao_3
#       UNION
#       SELECT titulo_eleitor, cpf, situacao_eleitor, data_filiacao, nome FROM filiacao_4
#     ) AS t
#     EOL
#     time rows pgexport --is-query $DATABASE_URL "$(cat /tmp/filiacao.sql)" data/output/filiacao_partidaria.csv.gz
#     rm /tmp/filiacao.sql

function log() {
	echo "[$(date --iso=seconds)] $@";
}
function execsql() {
	time echo "$@" | psql --no-psqlrc "$DATABASE_URL";
}

filiacao_csv="data/output/filiacao_partidaria.csv.gz"
candidatura_csv="data/output/candidatura.csv.gz"
final_csv_filename="data/output/candidatura_final.csv.gz"
if [[ -z $DATABASE_URL ]]; then
	echo "ERRO: variável DATABASE_URL não está configurada"
	exit 1
elif [[ ! -e $filiacao_csv ]]; then
	echo "ERRO: arquivo ${filiacao_csv} não existe"
	exit 2
elif [[ ! -e $candidatura_csv ]]; then
	echo "ERRO: arquivo ${candidatura_csv} não existe"
	exit 3
fi

echo "DROP TABLE IF EXISTS filiacao_orig" | psql --no-psqlrc "$DATABASE_URL"
rows pgimport \
	--input-encoding=utf-8 \
	--schema=:text: \
	--dialect=excel \
	"${filiacao_csv}" \
	"$DATABASE_URL" \
	filiacao_orig

echo "DROP TABLE IF EXISTS candidatura_orig" | psql --no-psqlrc "$DATABASE_URL"
rows pgimport \
	--input-encoding=utf-8 \
	--schema=schema/candidatura.csv \
	--dialect=excel \
	"${candidatura_csv}" \
	"$DATABASE_URL" \
	candidatura_orig

log "Criando tabela com mapeamento de títulos de eleitor com CPFs"
execsql "DROP TABLE IF EXISTS titulo_cpf"
query="
CREATE TABLE titulo_cpf AS
  WITH temp AS (
    SELECT DISTINCT
      c.titulo_eleitoral,
      RIGHT('00000000000' || f.cpf, 11) AS cpf,
      f.data_filiacao::date AS data
    FROM candidatura_orig AS c
    INNER JOIN filiacao_orig AS f
      ON c.titulo_eleitoral::bigint = f.titulo_eleitor::bigint
    WHERE
      COALESCE(f.titulo_eleitor, '') <> ''
      AND COALESCE(f.cpf, '') <> ''
    UNION
    SELECT DISTINCT
      c.titulo_eleitoral,
      RIGHT('00000000000' || c.cpf, 11) AS cpf,
      (c.ano || '-08-01')::date AS data
    FROM candidatura_orig AS c
    WHERE
      COALESCE(c.titulo_eleitoral, '') <> ''
      AND COALESCE(c.cpf, '') <> ''
      AND c.cpf <> '00000000004'
  )
  SELECT DISTINCT ON (titulo_eleitoral)
    titulo_eleitoral,
    cpf
  FROM temp
  ORDER BY titulo_eleitoral, data DESC
"
execsql "$query"

log "Criando tabela final de candidatura"
execsql "DROP TABLE IF EXISTS candidatura_final"
# TODO: o que fazer com o UUID nos casos em que o CPF fica em branco?
query="
CREATE TABLE candidatura_final AS
  SELECT
    person_uuid(cpf, nome) AS pessoa_uuid,
    *
  FROM (
    SELECT
      c.candidatura_uuid,
      c.ano,
      c.candidatura_inserida_urna,
      c.codigo_cargo,
      c.codigo_etnia,
      c.codigo_detalhe_situacao_candidatura,
      c.codigo_eleicao,
      c.codigo_estado_civil,
      c.codigo_genero,
      c.codigo_grau_instrucao,
      c.codigo_legenda,
      c.codigo_municipio_nascimento,
      c.codigo_nacionalidade,
      c.codigo_ocupacao,
      c.codigo_situacao_candidatura_pleito,
      c.codigo_situacao_candidatura_urna,
      c.codigo_situacao_candidatura,
      c.codigo_tipo_eleicao,
      c.codigo_totalizacao_turno,
      c.composicao_legenda,
      c.concorre_reeleicao,
      CASE
        WHEN COALESCE(c.cpf, '') IN ('', '4', '00000000004') THEN t.cpf
        ELSE c.cpf
      END AS cpf,
      c.data_eleicao,
      c.data_nascimento,
      c.declara_bens,
      c.cargo,
      c.etnia,
      c.detalhe_situacao_candidatura,
      c.eleicao,
      c.estado_civil,
      c.genero,
      c.grau_instrucao,
      c.nacionalidade,
      c.ocupacao,
      c.situacao_candidatura_pleito,
      c.situacao_candidatura_urna,
      c.situacao_candidatura,
      c.totalizacao_turno,
      c.unidade_eleitoral,
      c.despesa_maxima_campanha,
      c.email,
      c.idade_data_eleicao,
      c.idade_data_posse,
      c.nome,
      c.legenda,
      c.municipio_nascimento,
      c.partido,
      c.nome_social,
      c.tipo_eleicao,
      c.nome_urna,
      c.numero_partido,
      c.numero_processo_candidatura,
      c.numero_protocolo_candidatura,
      c.numero_sequencial,
      c.turno,
      c.numero_urna,
      c.pergunta,
      c.sigla_legenda,
      c.sigla_partido,
      c.sigla_unidade_eleitoral,
      c.sigla_unidade_federativa,
      c.sigla_unidade_federativa_nascimento,
      c.tipo_abrangencia_eleicao,
      c.tipo_agremiacao,
      c.titulo_eleitoral,
      c.federacao,
      c.federacao_composicao,
      c.federacao_numero,
      c.federacao_sigla,
      c.situacao_candidato_tot,
      c.codigo_situacao_candidato_tot,
      c.situacao_prestacao_contas,
      c.tipo_destinacao_votos,
      c.data_aceite,
      c.ordem_suplencia,
      c.sequencial_substituido,
      c.status_substituido
    FROM candidatura_orig AS c
    LEFT JOIN titulo_cpf AS t
      ON c.titulo_eleitoral::bigint = t.titulo_eleitoral::bigint
  ) AS t
"
execsql "$query"

log "Exportando tabela final de candidatura"
rows pgexport "$DATABASE_URL" "candidatura_final" "${final_csv_filename}"

log "Extraindo estatísticas"
select="
SELECT
  ano,
  COUNT(*) AS registros,
  COUNT(DISTINCT cpf) AS cpfs_distintos,
  COUNT(DISTINCT titulo_eleitoral) AS titulos_eleitorais_distintos
"
where="WHERE COALESCE(cpf, '') IN ('', '4', '00000000004')"
group_order="GROUP BY 1 ORDER BY 1"
log " -> Candidaturas com CPFs totais e distintos por ano (ANTES de cruzar com filiação + candidaturas históricas):"
execsql "${select} FROM candidatura_orig ${group_order}"
log " -> Candidaturas com CPFs totais e distintos por ano (DEPOIS de cruzar com filiação + candidaturas históricas):"
execsql "${select} FROM candidatura_final ${group_order}"
log " -> Candidaturas com CPFs em branco por ano (ANTES de cruzar com filiação + candidaturas históricas):"
execsql "${select} FROM candidatura_orig ${where} ${group_order}"
log " -> Candidaturas com CPFs em branco por ano (DEPOIS de cruzar com filiação + candidaturas históricas):"
execsql "${select} FROM candidatura_final ${where} ${group_order}"
