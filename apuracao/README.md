# Apuração em tempo real

Conjunto de scripts que auxilia a coleta de dados do TSE durante a apuração das
eleições e sobe para o Google Sheets.

Links úteis:

- [Planilha 1o turno](https://docs.google.com/spreadsheets/d/1Oy1mHo78313Ls1jSKayyVWW4KeqFyS94eg3LIIe1UXU/edit#gid=0)
- [Planilha 2o turno](https://docs.google.com/spreadsheets/d/1r9UmthUo9IPSLqNN89r_fhrsXo-igSjzCMv2sViwNZo/edit?usp=drive_web&ouid=105453500354565542048)
- [Planilha votos por município (1o/2o turnos) para presidente](https://docs.google.com/spreadsheets/d/1r9UmthUo9IPSLqNN89r_fhrsXo-igSjzCMv2sViwNZo/edit#gid=1826542857)
- [JSONs 1o e 2o turnos (data.zip)](https://gist.github.com/turicas/4b9617a74ac3cf86bd055e461afc6c46)
- [Tweet acompanhamento 1o turno](https://twitter.com/turicas/status/1576685227313082368)
- [Tweet acompanhamento 2o turno](https://twitter.com/turicas/status/1586826575344959494)


## Rodando

### Atualiza planilhas

Baixa dados da API do TSE e atualiza planilhas no Google Sheets (necessita de
arquivo `credentials/eleicoes-2022-brasil-io-sheets.json`):

```sh
python apuracao.py [--print-only] <1|2> <governador|presidente>
```

### Baixa municípios e códigos

Baixa arquivo de votação por seção eleitoral de 2022 para extrair os códigos de
município e gerar o arquivo `municipios-tse.csv`, que é utilizado em
outros scripts.

```sh
python municipios_tse.py
```

### Consolida votação presidencial por município

Usando os códigos de município disponíveis em `municipios-tse.csv`, baixa
dados da API de tempo real do TSE do primeiro e segundo turno para consolidar
os votos por município para Lula e Bolsonaro, salvo em
`data/votacao-presidencial-por-municipio.csv`.

```sh
python votacao_municipio.py
```
