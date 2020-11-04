#!/bin/bash

set -e
mkdir -p data/download
rm -rf data/download/SHA512SUMS

mkdir -p data/download/bem_candidato
time aria2c -s 8 -x 8 -k 1M -o 'data/download/bem_candidato/bem_candidato_2006.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2006.zip'
time s3cmd put 'data/download/bem_candidato/bem_candidato_2006.zip' s3://mirror/tse/bem_candidato/bem_candidato_2006.zip
time echo "$(sha512sum 'data/download/bem_candidato/bem_candidato_2006.zip' | cut -d' ' -f 1) bem_candidato/bem_candidato_2006.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/bem_candidato/bem_candidato_2008.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2008.zip'
time s3cmd put 'data/download/bem_candidato/bem_candidato_2008.zip' s3://mirror/tse/bem_candidato/bem_candidato_2008.zip
time echo "$(sha512sum 'data/download/bem_candidato/bem_candidato_2008.zip' | cut -d' ' -f 1) bem_candidato/bem_candidato_2008.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/bem_candidato/bem_candidato_2010.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2010.zip'
time s3cmd put 'data/download/bem_candidato/bem_candidato_2010.zip' s3://mirror/tse/bem_candidato/bem_candidato_2010.zip
time echo "$(sha512sum 'data/download/bem_candidato/bem_candidato_2010.zip' | cut -d' ' -f 1) bem_candidato/bem_candidato_2010.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/bem_candidato/bem_candidato_2012.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2012.zip'
time s3cmd put 'data/download/bem_candidato/bem_candidato_2012.zip' s3://mirror/tse/bem_candidato/bem_candidato_2012.zip
time echo "$(sha512sum 'data/download/bem_candidato/bem_candidato_2012.zip' | cut -d' ' -f 1) bem_candidato/bem_candidato_2012.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/bem_candidato/bem_candidato_2014.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2014.zip'
time s3cmd put 'data/download/bem_candidato/bem_candidato_2014.zip' s3://mirror/tse/bem_candidato/bem_candidato_2014.zip
time echo "$(sha512sum 'data/download/bem_candidato/bem_candidato_2014.zip' | cut -d' ' -f 1) bem_candidato/bem_candidato_2014.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/bem_candidato/bem_candidato_2016.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2016.zip'
time s3cmd put 'data/download/bem_candidato/bem_candidato_2016.zip' s3://mirror/tse/bem_candidato/bem_candidato_2016.zip
time echo "$(sha512sum 'data/download/bem_candidato/bem_candidato_2016.zip' | cut -d' ' -f 1) bem_candidato/bem_candidato_2016.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/bem_candidato/bem_candidato_2018.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2018.zip'
time s3cmd put 'data/download/bem_candidato/bem_candidato_2018.zip' s3://mirror/tse/bem_candidato/bem_candidato_2018.zip
time echo "$(sha512sum 'data/download/bem_candidato/bem_candidato_2018.zip' | cut -d' ' -f 1) bem_candidato/bem_candidato_2018.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/bem_candidato/bem_candidato_2020.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2020.zip'
time s3cmd put 'data/download/bem_candidato/bem_candidato_2020.zip' s3://mirror/tse/bem_candidato/bem_candidato_2020.zip
time echo "$(sha512sum 'data/download/bem_candidato/bem_candidato_2020.zip' | cut -d' ' -f 1) bem_candidato/bem_candidato_2020.zip" >> data/download/SHA512SUMS

mkdir -p data/download/consulta_cand
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_1996.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_1996.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_1996.zip' s3://mirror/tse/consulta_cand/consulta_cand_1996.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_1996.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_1996.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_1998.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_1998.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_1998.zip' s3://mirror/tse/consulta_cand/consulta_cand_1998.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_1998.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_1998.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_2000.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2000.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_2000.zip' s3://mirror/tse/consulta_cand/consulta_cand_2000.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_2000.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_2000.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_2002.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2002.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_2002.zip' s3://mirror/tse/consulta_cand/consulta_cand_2002.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_2002.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_2002.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_2004.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2004.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_2004.zip' s3://mirror/tse/consulta_cand/consulta_cand_2004.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_2004.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_2004.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_2006.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2006.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_2006.zip' s3://mirror/tse/consulta_cand/consulta_cand_2006.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_2006.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_2006.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_2008.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2008.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_2008.zip' s3://mirror/tse/consulta_cand/consulta_cand_2008.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_2008.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_2008.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_2010.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2010.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_2010.zip' s3://mirror/tse/consulta_cand/consulta_cand_2010.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_2010.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_2010.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_2012.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2012.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_2012.zip' s3://mirror/tse/consulta_cand/consulta_cand_2012.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_2012.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_2012.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_2014.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2014.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_2014.zip' s3://mirror/tse/consulta_cand/consulta_cand_2014.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_2014.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_2014.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_2016.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2016.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_2016.zip' s3://mirror/tse/consulta_cand/consulta_cand_2016.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_2016.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_2016.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_2018.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2018.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_2018.zip' s3://mirror/tse/consulta_cand/consulta_cand_2018.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_2018.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_2018.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/consulta_cand/consulta_cand_2020.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2020.zip'
time s3cmd put 'data/download/consulta_cand/consulta_cand_2020.zip' s3://mirror/tse/consulta_cand/consulta_cand_2020.zip
time echo "$(sha512sum 'data/download/consulta_cand/consulta_cand_2020.zip' | cut -d' ' -f 1) consulta_cand/consulta_cand_2020.zip" >> data/download/SHA512SUMS

mkdir -p data/download/prestacao_contas
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_contas_2002.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_contas_2002.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_contas_2002.zip' s3://mirror/tse/prestacao_contas/prestacao_contas_2002.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_contas_2002.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_contas_2002.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_contas_2004.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_contas_2004.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_contas_2004.zip' s3://mirror/tse/prestacao_contas/prestacao_contas_2004.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_contas_2004.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_contas_2004.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_contas_2006.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_contas_2006.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_contas_2006.zip' s3://mirror/tse/prestacao_contas/prestacao_contas_2006.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_contas_2006.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_contas_2006.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_contas_2008.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_contas_2008.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_contas_2008.zip' s3://mirror/tse/prestacao_contas/prestacao_contas_2008.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_contas_2008.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_contas_2008.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_contas_2010.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_contas_2010.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_contas_2010.zip' s3://mirror/tse/prestacao_contas/prestacao_contas_2010.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_contas_2010.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_contas_2010.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_final_2012.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_final_2012.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_final_2012.zip' s3://mirror/tse/prestacao_contas/prestacao_final_2012.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_final_2012.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_final_2012.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_final_2014.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_final_2014.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_final_2014.zip' s3://mirror/tse/prestacao_contas/prestacao_final_2014.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_final_2014.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_final_2014.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_contas_final_sup_2014.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_contas_final_sup_2014.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_contas_final_sup_2014.zip' s3://mirror/tse/prestacao_contas/prestacao_contas_final_sup_2014.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_contas_final_sup_2014.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_contas_final_sup_2014.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_contas_final_2016.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_contas_final_2016.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_contas_final_2016.zip' s3://mirror/tse/prestacao_contas/prestacao_contas_final_2016.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_contas_final_2016.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_contas_final_2016.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2018.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2018.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2018.zip' s3://mirror/tse/prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2018.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2018.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2018.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2018.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2018.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2018.zip' s3://mirror/tse/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2018.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2018.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2018.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2020.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2020.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2020.zip' s3://mirror/tse/prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2020.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2020.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2020.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2020.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2020.zip'
time s3cmd put 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2020.zip' s3://mirror/tse/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2020.zip
time echo "$(sha512sum 'data/download/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2020.zip' | cut -d' ' -f 1) prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2020.zip" >> data/download/SHA512SUMS


mkdir -p data/download/votacao_candidato_munzona
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_1996.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_1996.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_1996.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_1996.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_1996.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_1996.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_1998.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_1998.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_1998.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_1998.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_1998.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_1998.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2000.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2000.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2000.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_2000.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2000.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_2000.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2002.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2002.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2002.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_2002.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2002.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_2002.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2004.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2004.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2004.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_2004.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2004.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_2004.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2006.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2006.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2006.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_2006.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2006.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_2006.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2008.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2008.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2008.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_2008.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2008.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_2008.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2010.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2010.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2010.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_2010.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2010.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_2010.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2012.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2012.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2012.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_2012.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2012.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_2012.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2014.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2014.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2014.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_2014.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2014.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_2014.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2016.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2016.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2016.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_2016.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2016.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_2016.zip" >> data/download/SHA512SUMS
time aria2c -s 8 -x 8 -k 1M -o 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2018.zip' 'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2018.zip'
time s3cmd put 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2018.zip' s3://mirror/tse/votacao_candidato_munzona/votacao_candidato_munzona_2018.zip
time echo "$(sha512sum 'data/download/votacao_candidato_munzona/votacao_candidato_munzona_2018.zip' | cut -d' ' -f 1) votacao_candidato_munzona/votacao_candidato_munzona_2018.zip" >> data/download/SHA512SUMS

