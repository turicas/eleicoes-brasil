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
não coloque conteúdo manual nelas. Nas abas de resultados, cabeçalho e rótulos
ficam em negrito, quantidades usam `#,##0`, percentuais usam `0.00%`, valores do
resumo ficam à direita e as linhas de eleitorado e seções totalizadas têm fundo
cinza.
linhas têm 21 pixels e cabeçalho congelado. A fonte é Source Code Pro, tamanho 10,
e todas as colunas são ajustadas automaticamente ao conteúdo, incluindo a linha
do tempo. A formatação é aplicada apenas ao criar abas ou executar o ajuste visual,
nunca na atualização frequente. A cada dez publicações bem-sucedidas, cada rotina
refaz apenas o ajuste automático das colunas de todas as abas, no mesmo lote;
falhas e ciclos sem geração nova não contam. Outros formatos são preservados. Se o número de
candidatos mudar, execute o ajuste visual para reposicionar os estilos do resumo.
Estrutura, formato e valores são enviados em um lote atômico. Execute um único escritor
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

### Acompanhamento rápido

Pare o loop bash antigo antes de iniciar:

```sh
python -m apuracao.acompanhamento 2026 1
```

O gerenciador usa o ID cadastrado para ano/turno e procura as credenciais em
`apuracao/credentials/eleicoes-2026-brasil-io-sheets.json`, com preferência por
`GOOGLE_APPLICATION_CREDENTIALS` se definida. Presidente inicia consultas a cada
25 segundos em processo próprio; as UFs são consultadas a cada 60 segundos, com
seis conexões paralelas e até 20 inícios de consulta por segundo. Uma rotina não
espera pela outra. Os intervalos são início-a-início, sem somar o tempo de execução;
slots perdidos por falha/lentidão não se acumulam. Redes e API indisponíveis podem
impedir a conclusão no prazo, mas UFs lentas não atrasam presidente.

Clientes, contexto, conexões e metadados são reutilizados. A publicação normal
altera valores e título, não formato. Só gerações novas são enviadas ao Sheets;
uma falha de publicação não marca a geração como concluída. Cache busting das
consultas ao TSE usa `?_=time.time_ns()` (ou `&_=...`) com `Cache-Control: no-cache`
e `Pragma: no-cache`. Isso não faz o TSE produzir uma geração nova. A data/hora do
histórico é a geração da fonte, não o horário de cada consulta.

Presidente e UFs mostram "Eleitorado que falta apurar": em 2026 usa-se `e.esnt`,
eleitorado das seções ainda não totalizadas, com separador de milhar. Seções não
instaladas já totalizadas não são pendências. Não representa votos garantidos,
pois inclui possíveis abstenções. Campo ausente fica vazio; a soma por UF conserva
essa ausência. Em 2022 mantém-se o cálculo histórico de total menos apurado.

As abas das UFs mostram o percentual de seções totalizadas e o indicador de
apuradas dividido pelo total, com nomes distintos. LinhaDoTempo guarda data/hora
numericamente e exibe apenas `HH:mm:ss`, preservando o dia no valor subjacente.
Suas colunas são data/hora, percentual de seções totalizadas, Lula, Flávio e os
demais candidatos. Ao mudar a ordem, o gráfico administrado é remapeado no mesmo
lote dos valores, sem alterar seus ajustes visuais.

```sh
python -m apuracao.acompanhamento 2026 1 --intervalo-presidente 20 --intervalo-ufs 30
```

Para substituir o JSON nacional pela soma das fontes presidenciais de cada UF e
do exterior:

```sh
python -m apuracao.acompanhamento 2026 1 --presidente-por-uf
```

Esse modo exige as 28 fontes completas e compatíveis a cada coleta; se uma falhar,
não publica uma soma parcial. A data/hora da linha do tempo e do título é a hora real da coleta do agregado.
A maior e a menor geração das fontes ficam separadas no resumo: estados podem
mudar sem ultrapassar o maior horário anterior, portanto ele não identifica a
captura. Arquivos agregados antigos usam o horário de gravação local como
aproximação, pois não registravam a captura explicitamente.
A aba também identifica a origem como soma própria,
não consolidado nacional do TSE. Percentuais são recalculados com a soma dos votos
a concorrentes, não com a soma de percentuais. O título mantém essa identificação.

As abas de resultados ficam verdes quando há eleito definido, azuis quando há
segundo turno definido e pretas enquanto não há definição. Usa-se `md` oficial;
após totalização final, a situação dos candidatos mantém a definição. Na soma
presidencial, consulta-se o JSON nacional só para a cor, sem inferir vitória a
partir das UFs. Se essa consulta falhar, a cor anterior é preservada e os votos
continuam atualizando. A cor muda no mesmo lote dos dados, sem reformatar células.
A aba LinhaDoTempo não é colorida por essa regra. UFs com `tf=s` recebem
asterisco no nome (ex.: `AC*`), independentemente da cor de MD. O publicador
reconhece nomes com/sem asterisco e renomeia o mesmo sheetId, sem criar duplicatas.
Se TF reverter, remove o asterisco. Reinicie processos antigos antes de renomear
abas: seus caches de nomes não conhecem essa convenção.
Os brutos desse modo são separados, persistidos em `ANO/turno-N/soma-presidente/`
e retomados ao reiniciar. A linha do tempo reúne os registros nacionais e os
agregados, sem apagar as linhas anteriores ao trocar de modo.

### Seleção automática pela cobertura

```sh
python -m apuracao.acompanhamento 2026 1 --presidente-automatico --intervalo-presidente 10 --intervalo-ufs 30
```

Consulta nacional e 27 UFs + exterior. Escolhe o resultado completo com mais
seções totalizadas, exigindo o mesmo total geral; nacional vence em empate.
Não mistura votos de um conjunto com totais do outro. Uma UF indisponível impede
a soma, mas não a publicação nacional. O lote paralelo das UFs tem no máximo dois
segundos de espera por ciclo; quando ainda pendente, não se inicia outro lote e o
nacional pode ser publicado. A comparação não presume que maior horário significa
maior cobertura, nem impede correções oficiais que reduzam totais.

A consulta nacional também alimenta MD/TF e cor, sem requisição duplicada.
O histórico anterior é preservado, a coluna Origem fica depois dos candidatos e
as escolhas novas são persistidas em `historico-presidente-selecionado.jsonl`.
Ao reiniciar, esse registro evita inserir no histórico somas que não foram escolhidas.
O modo automático conserva a última soma completa entre rodadas regionais e a última
resposta nacional válida diante de falhas temporárias. Uma rodada incompleta ou com
falhas não substitui a soma anterior nem produz uma soma parcial. As fontes originais
e seus horários são preservados; reutilizar um resultado não cria uma geração nova
na linha do tempo.

As opções `--presidente-automatico` e `--presidente-por-uf` são mutuamente exclusivas.

No Linux, cada trabalhador recebe SIGKILL do kernel se o pai morrer, com verificação
da corrida de inicialização. Ctrl+C usa o encerramento limitado já implementado;
segundo sinal força os filhos. A proteção não cobre processos antigos iniciados
antes desta versão.

O arquivo de lock impede dois gerenciadores para a mesma planilha/diretório; não
bloqueia o loop bash antigo nem programas externos. Ctrl+C encerra os processos;
um segundo sinal força o encerramento dos filhos. O tratador não usa Event.set(),
pois pode causar deadlock se interromper a espera no mesmo evento.
O segundo turno de 2026 exige cadastrar seu ID antes de usar este comando.

O comando `python -m apuracao` continua fazendo uma coleta e terminando.
Não existem IDs antigos como destino implícito nesse comando avulso.
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

### Aba LEIA-ME

Cria ou atualiza autoria, redes sociais, fontes e legenda, colocando a aba em
primeiro lugar sem modificar resultados/histórico:

```sh
python -m apuracao.leia_me 2026 1 1RGi20p_QECrdRo_KJgxhSDo7zO2wnIFuxRqKs2XrWa0 \
    --intervalo-presidente 10 --intervalo-ufs 30
```

Os intervalos documentados devem corresponder aos argumentos do gerenciador;
sem parâmetros, o texto informa que a frequência é configurável. A aba não é
reescrita em cada captura. Se mudar o ritmo, execute este comando novamente.

### Ajuste visual pontual e gráfico

O script usa as mesmas regras de formato do publicador, sem alterar valores.
Sem `--aplicar`, apenas lê a planilha e grava os pedidos planejados em
`data/analise-apuracao-2026/`. A API autoriza o lote, mas o script não altera
permissões nem a configuração regional.

```sh
export GOOGLE_APPLICATION_CREDENTIALS="$PWD/apuracao/credentials/eleicoes-2026-brasil-io-sheets.json"
python -m apuracao.ajuste_visual 1RGi20p_QECrdRo_KJgxhSDo7zO2wnIFuxRqKs2XrWa0 --aplicar
python -m apuracao.ajuste_visual 1RGi20p_QECrdRo_KJgxhSDo7zO2wnIFuxRqKs2XrWa0 --grafico --aplicar
```

O segundo comando prepara somente o gráfico de linhas Lula/Flávio em
`LinhaDoTempo`, identificando as colunas pelo nome e número, não por letras
fixas. Flávio fica azul e Lula vermelho, com legenda superior e data/hora no eixo
X. Reaproveita o gráfico correspondente ou o gráfico vazio, sem apagar outros.
O mínimo do eixo Y fica em 0,40. A coluna de domínio mostra só a hora; strings
ISO antigas são convertidas para seriais locais sem perder a data. A rotação dos
rótulos X não é exposta pela API v4: no editor, use Personalizar > Eixo horizontal
> Inclinar rótulos e ajuste o ângulo para 90°, se essa opção estiver disponível.
A criação desse gráfico é específica da disputa de 2026, não automática para
outros anos. O publicador expande suas fontes se o histórico ultrapassar a grade
atual, sem criar outro gráfico. Não é necessário alterar o intervalo a cada coleta.

Fonte da estrutura dos pedidos: [Google Sheets - gráficos](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/charts).

### Segundo turno de 2026

A planilha do segundo turno é [Apuração Eleições 2026 - 2º turno](https://docs.google.com/spreadsheets/d/1B7tb4yJv8qoJEVoK-TkSQs8n7YewFSGXkhA7LEGFOLQ/edit).
Usa as mesmas credenciais de 2026 e mantém histórico separado por turno.

```sh
python -m apuracao.acompanhamento 2026 2 --presidente-automatico --intervalo-presidente 10 --intervalo-ufs 30
```

As eleições e as UFs são descobertas na configuração oficial EA11, exigindo uma eleição
publicada de turno 2, sem inferir sua existência apenas por `cdt2`. Presidente é o cargo 1
na eleição federal ordinária; governador é o cargo 3 na eleição estadual ordinária.
No snapshot de 18/10/2026, os códigos são 6258 e 6260, e as UFs estaduais publicadas
são AC, AM, DF, ES, RN e TO. Eleições suplementares e consultas populares não entram
nesse acompanhamento. A linha do tempo presidencial fica na aba `LinhaDoTempo`.
A apresentação fica na primeira aba, `LEIA-ME`, com um exemplo de governo realmente
em disputa e a lista de abrangências descoberta no TSE. Sua preparação é independente
das atualizações frequentes:

```sh
python -m apuracao.leia_me 2026 2 1B7tb4yJv8qoJEVoK-TkSQs8n7YewFSGXkhA7LEGFOLQ \
    --intervalo-presidente 10 --intervalo-ufs 30
```

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
