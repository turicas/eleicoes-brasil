# Apuração em tempo real

Coleta a apuração oficial de presidente e governador em 2022 e 2026, preserva
arquivos locais e atualiza uma planilha existente no Google Sheets. Os adaptadores
retornam objetos de domínio; download, apresentação e publicação são separados.

Planilhas de 2026:

- [Planilha 1º turno](https://docs.google.com/spreadsheets/d/1RGi20p_QECrdRo_KJgxhSDo7zO2wnIFuxRqKs2XrWa0/edit)

Links históricos de 2022:

- [Planilha 1o turno](https://docs.google.com/spreadsheets/d/1Oy1mHo78313Ls1jSKayyVWW4KeqFyS94eg3LIIe1UXU/edit#gid=0)
- [Planilha 2o turno](https://docs.google.com/spreadsheets/d/1r9UmthUo9IPSLqNN89r_fhrsXo-igSjzCMv2sViwNZo/edit?usp=drive_web&ouid=105453500354565542048)
- [Planilha votos por município (1o/2o turnos) para presidente](https://docs.google.com/spreadsheets/d/1r9UmthUo9IPSLqNN89r_fhrsXo-igSjzCMv2sViwNZo/edit#gid=1826542857)
- [JSONs 1o e 2o turnos (data.zip)](https://gist.github.com/turicas/4b9617a74ac3cf86bd055e461afc6c46)
- [Tweet acompanhamento 1o turno](https://twitter.com/turicas/status/1576685227313082368)
- [Tweet acompanhamento 2o turno](https://twitter.com/turicas/status/1586826575344959494)


## Rodando

### Atualiza planilhas

Execute os comandos a partir da raiz do repositório. Instale as dependências:

```sh
python -m pip install -r apuracao/requirements.txt
```

Crie uma planilha vazia por turno. Compartilhe-a como editor com o `client_email`
da conta de serviço e habilite a Google Sheets API no projeto da conta. Não é
necessário gerar outra credencial só porque mudou o ano. Informe o caminho do
arquivo por variável de ambiente, nunca seu conteúdo na linha de comando:

```sh
export GOOGLE_APPLICATION_CREDENTIALS="$PWD/apuracao/credentials/eleicoes-2026-brasil-io-sheets.json"
python -m apuracao 2026 1 presidente 1RGi20p_QECrdRo_KJgxhSDo7zO2wnIFuxRqKs2XrWa0
python -m apuracao 2026 1 governador 1RGi20p_QECrdRo_KJgxhSDo7zO2wnIFuxRqKs2XrWa0
```

O nome recomendado para as credenciais é `eleicoes-2026-brasil-io-sheets.json`,
preservando o padrão histórico `eleicoes-2022-brasil-io-sheets.json`. O caminho
agora é configurado por `GOOGLE_APPLICATION_CREDENTIALS`, não fixado no código.

Para atualizar presidente continuamente, com cinco segundos de espera depois de
cada execução e interrupção no primeiro erro:

```sh
export GOOGLE_APPLICATION_CREDENTIALS="$PWD/apuracao/credentials/eleicoes-2026-brasil-io-sheets.json"
while true; do
    python -m apuracao 2026 1 presidente 1RGi20p_QECrdRo_KJgxhSDo7zO2wnIFuxRqKs2XrWa0
    resultado=$?
    if [ "$resultado" -ne 0 ]; then
        break
    fi
    sleep 5
done
```

O ID é o trecho entre `/d/` e `/edit` da URL da planilha. O programa cria as abas
`Presidente`, `LinhaDoTempo` e as UFs pertinentes conforme o cargo executado, com
cabeçalhos, dimensões e formato percentual. Repetir a execução reutiliza as abas.
Abas alheias são preservadas. A publicação presidencial atualiza o título com o
percentual de seções totalizadas (apuradas em 2022) e o horário de geração do TSE;
a publicação de governador não altera o título. Ano e turno ficam registrados
em metadados: tentar reutilizar a planilha em outro contexto gera erro.

Os valores das abas administradas são substituídos, incluindo limpeza de sobras;
não coloque conteúdo manual nelas. Formatos não solicitados são preservados.
Estrutura e valores são enviados em um lote atômico. Execute um único escritor
por planilha; não há coordenação entre processos concorrentes.

Para uma UF ou para coletar sem Google:

```sh
python -m apuracao 2026 1 governador ID_DA_PLANILHA --uf SP
python -m apuracao 2026 1 presidente --print-only
```

`--print-only` emite JSON no stdout e não autentica no Google, mas baixa e salva
os dados localmente. Mensagens de erro ficam no stderr. Sucesso é silencioso na
publicação; códigos de saída: `0` sucesso, `1` falha (inclusive parcial por UF),
`2` argumentos inválidos, `130` interrupção. Uma UF com falha não apaga sua aba
anterior nem impede a atualização das demais UFs válidas.

A execução faz uma coleta e termina: agende novas execuções sem sobreposição,
por exemplo a cada minuto. Não existem os IDs antigos como destino implícito.
O comando direto também funciona: `python apuracao/apuracao.py 2026 1 presidente ID`.
A CLI antiga mudou: ano e ID agora são entradas explícitas.

Em 2026, a descoberta usa [EA11](https://resultados.tse.jus.br/oficial/comum/config/ele-c.json)
e [EA12](https://www.tse.jus.br/eleicoes/eleicoes-2026-content/arquivos/divulgacao-de-resultados),
e a leitura usa EA20 (`-u.json`). O segundo turno precisa estar publicado como
uma eleição própria na configuração; `cdt2` sozinho não autoriza gerar URLs.
O andamento, a totalização final e a definição matemática permanecem distintos.
Percentuais dos candidatos vêm do TSE, sem recalcular com denominador diferente.
Quando `dv=n`, a planilha informa que aguarda liberação, sem apresentar votos
zerados como resultados. A linha do tempo usa seções totalizadas em 2026; em 2022,
preserva o indicador antigo de seções apuradas dividido pelo total.

Os arquivos ficam em `apuracao/data/ANO/turno-N/cargo-C/UF/`, ou no diretório
indicado por `--data-path DIR`. O JSON é persistido atomicamente, preservando
campos da fonte, e o histórico é ordenado pela geração e deduplicado. Os arquivos
antigos diretamente em `apuracao/data/` não são migrados automaticamente.
O adaptador de 2022 verifica os metadados de identidade quando disponíveis;
campos ausentes em arquivos antigos não são inventados.

Regras de consumo: máximo de 100 requisições por IP por segundo no TSE; URLs
incorretas também podem causar bloqueio. O coletor é sequencial e limita tentativas.
O Sheets tem cotas de 60 leituras e 60 escritas por minuto por usuário/projeto;
a publicação em lote reduz chamadas. Falhas transitórias têm repetição limitada.
Históricos muito grandes podem exigir divisão em lotes; não há divisão automática.
Assinaturas JWS não são verificadas por esta implementação.

Fontes: [manuais do TSE](https://www.tse.jus.br/eleicoes/eleicoes-2026-content/arquivos/divulgacao-de-resultados),
[autenticação gspread](https://docs.gspread.org/en/latest/oauth2.html) e
[cotas Google Sheets](https://developers.google.com/workspace/sheets/api/limits).

### Testes

```sh
python -m pytest apuracao -o addopts='' -q
```

Os testes usam dados sintéticos, HTTP simulado e cliente Google em memória, sem
credenciais, rede ou esperas reais. As funções históricas de `apuracao.py` seguem
como ponte de compatibilidade; o fluxo novo usa `Resultado` e os adaptadores.

### Scripts auxiliares históricos

Os dois scripts abaixo continuam específicos de 2022. Não são usados pela CLI
nova nem foram migrados para 2026.

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
