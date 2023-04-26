#!/bin/bash

mkdir -p data/download
cd data/download
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_AC.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_AL.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_AM.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_AP.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_BA.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_BR.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_CE.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_ES.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_GO.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_MA.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_MG.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_MS.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_MT.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_PA.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_PB.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_PE.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_PI.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_PR.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_RJ.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_RN.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_RO.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_RR.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_RS.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_SC.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_SE.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_SP.zip'
wget -c -t 0 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2022_TO.zip'

rm rede_social_candidato_2022*.csv
for filename in rede_social_candidato_2022*.zip; do
    unzip "$filename" "$(basename $filename | sed 's/.zip$/.csv/')"
done
cd -

echo "DROP TABLE IF EXISTS rede_social_candidato" | psql --no-psqlrc $DATABASE_URL
for filename in data/download/rede_social_candidato_2022*.csv; do
    rows pgimport -s ':text:' -d 'excel-semicolon' -e 'iso-8859-1' \
            "$filename" "$DATABASE_URL" 'rede_social_candidato'
done
