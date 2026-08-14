# AGENTS.md

> Pipeline reprodutível de dados eleitorais brasileiros: baixa arquivos do TSE, preserva sua proveniência e os normaliza em CSVs históricos consistentes para análise.

## Comandos

- Testes: `make test` ou `pytest`
- Lint e formatação: `make lint`; apenas verificação: `make lint-check`
- Extração: `make tse ARGS='candidatura --years=2024'`
- Pipeline completo: `make run`; com _mirror_: `make run ARGS='--use-mirror'`
- Ambiente em container: `make build`, `make bash`
- Dentro do shell do container, `make test`, `make lint`, `make lint-check`, `make tse` e `make run` executam diretamente, sem iniciar outro container. Alvos que administram o Compose (`build`, `start`, `stop` etc.) não estão disponíveis para execução de dentro do container, apenas na máquina que possui Docker.

## PDFs

- A imagem de desenvolvimento inclui `poppler-utils`. Extraia texto com `pdftotext -layout -nopgbrk -enc UTF-8 -- "$pdf" "$txt"` e renderize páginas com `pdftocairo -png -r 300 -- "$pdf" "$output_dir/pagina"` para inspeção visual.
- Não conclua a análise apenas pelo texto extraído quando o PDF puder conter tabelas, imagens ou gráficos relevantes.

## Dados e normalização

- Trate os arquivos do TSE como fonte primária e volátil. Antes de suportar ano, arquivo ou coluna novos, inspecione o ZIP real, seus arquivos internos, encoding, dialeto e dicionário de dados/leiame quando existir.
- Não deduza formato, encoding, significado ou limpeza a partir de poucas linhas. Formule a hipótese, valide-a na base inteira e cubra o comportamento com teste quando couber.
- Passe encoding e dialeto explicitamente depois de confirmá-los. Não faça correções heurísticas de encoding ou texto sem evidência verificável.
- Os arquivos em `headers/` são o dicionário de dados versionado: preservam o nome do TSE, mapeiam-no para o nome final e documentam a semântica. Os nomes finais devem ser intuitivos, específicos, em português, sem acentos e em `snake_case` - não reproduza abreviações opacas do TSE.
- Nomenclatura de colunas em tabelas/saídas novas:
  - Se a coluna se refere ao próprio registro representado na tabela, não incluir o nome da tabela (ex.: na tabela `candidatura`, `CANDIDATURA_NOME_URNA` vira `nome_urna`).
  - Se a coluna se refere a uma entidade externa contida no registro, prefixar com o nome da entidade (ex.: `partido_sigla`, `partido_numero`, `eleicao_codigo`, `fornecedor_cpf_cnpj`), garantindo que atributos da mesma entidade externa fiquem agrupados alfabeticamente.
  - A tabela `candidatura` existente mantém seus nomes históricos por compatibilidade com consumidores externos, mas todas as tabelas novas devem seguir estritamente essa regra.
- Não remova nem renomeie campos silenciosamente. Para campo sem significado confirmado, preserve-o, registre `TODO` claro ou peça decisão. Campo omitido da saída deve continuar documentado no header por ano.
- Após alterar headers por ano, regenere os dicionários finais com `python tse.py headers` e revise o resultado.
- `schema/` define os tipos e a ordem lógica de cada saída consolidada. Atualize schema, header final e conversão juntos quando um campo final mudar.
- Preserve compatibilidade histórica. A normalização atual de maiúsculas/acentos existe em dados já publicados; não a amplie nem a altere globalmente sem decisão explícita e plano de migração. Dados novos destinados à apresentação não devem perder acentos/capitalização sem necessidade comprovada.
- Valores sentinela do TSE (`#NULO`, `#NULO#`, `#NE`, `#NE#`, `-1`, `-3`, `-4`, `NÃO DIVULGÁVEL`), datas, documentos e valores financeiros exigem normalização explícita: todas as sentinelas de ausência devem virar vazio `""` no CSV consolidado final.
- Em conjuntos que publicam arquivos por UF e também o consolidado `_BRASIL.` (como detalhe de votação e prestação anual), ignorar `_BRASIL.` e processar apenas UFs + `BR`, evitando duplicação.
- Arquivos anuais do TSE que contenham apenas o cabeçalho (sem registros) devem ser tratados como _snapshots_ válidos, sem levantar exceção de arquivo vazio.
- `data/` contém downloads e saídas locais, ignorados pelo Git. Versione código, headers, schemas, testes e documentação - não os CSVs/ZIPs gerados.
- Brutos em `data/download/` (`settings.DOWNLOAD_PATH`); normalizados em `data/output/`. O caminho relativo do ZIP espelha o path em `odsele/` e vem de `Extractor.filename()` em `extractors.py` - não adivinhe pelo nome amigável do produto (candidatura não se chama `candidatura` no TSE). Exemplos estáveis: candidatura -> `consulta_cand/consulta_cand_{ano}.zip`; bem declarado -> `bem_candidato/bem_candidato_{ano}.zip`; votação por zona -> `votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip`. Prestação de contas muda o path por ano no próprio extractor.
- O nome canônico (sem data extra) é o que o pipeline consome. Para guardar um snapshot sem sobrescrever o canônico, use sufixo de data no filename, ex.: `consulta_cand_2026_2026-08-13.zip`.
- Proveniência temporal do bruto: nos CSVs originais, em geral `DT_GERACAO` e `HH_GERACAO` (encoding `latin-1`, delimitador `;`). No HTTP, `Last-Modified`/`ETag`/`Content-Length` falam da publicação no CDN; mtime das entries do ZIP, do empacotamento; mtime local do arquivo, só de quando baixamos - não confunda os três.

## Entidades e UUIDs

- UUID identifica uma entidade, não uma linha de CSV nem necessariamente uma chave primária da saída. Uma pessoa ou candidatura pode aparecer em muitos registros.
- Para UUID novo, defina e revise antes a entidade, o Raw ID estável, a versão e a URL de namespace. Use UUID v5 conforme a metodologia [URLid](https://urlid.org/); não invente identificadores a partir de campos instáveis.
- Reutilize os UUIDs de pessoa e candidatura já existentes quando a entidade for a mesma. Ao encontrar entidade sem identificador definido, adicione `TODO` específico em vez de criar UUID especulativo.

## Código, CLI e testes

- Siga o estilo local antes de introduzir abstrações. Prefira `pathlib.Path`, `csv` e dependências já adotadas; não introduza `pandas` para processar CSV.
- Mantenha o extractor genérico separado das particularidades de ano, tipo de arquivo e mapeamento de headers. Não esconda diferenças históricas em condicionais sem teste e documentação.
- Lógica de transformação deve ser pequena, determinística e exercitável sem download. Trate erros de dados com contexto suficiente para localizar arquivo, ano e coluna.
- Para comportamento novo ou corrigido, use TDD red/green: escreva primeiro o teste da API/comportamento esperado, execute-o para observar a falha, implemente o mínimo e execute novamente. Teste comportamento e regressões de dados, não detalhes internos.
- `pytest` executa testes e doctests. Preserve os testes existentes e acrescente casos para formatos históricos, sentinelas, conversões e incompatibilidades de header relevantes.
- Fixtures para testes devem ser sintéticas e mínimas, reproduzindo formato e sentinelas necessárias sem incluir certidões ou imagens reais de cidadãos no repositório.
- Separação de canais: dados estruturados no `stdout`; mensagens de _status_, progresso e erros no `stderr`. Respeite a _Rule of Silence_ (sucesso silencioso com código `0`).
- Estrutura CLI: use `argparse` da _stdlib_; isole a construção do parser em função dedicada (`cria_parser()` ou `_configura_parser_cli()`); sem código no corpo do módulo (`if __name__ == "__main__":` obrigatório). Desacople lógica de negócio de I/O de terminal.
- Parâmetros e opções: argumentos obrigatórios são posicionais; opções `--` apenas para parâmetros opcionais em _kebab-case_ (com opção curta `-` pareada quando útil). Use `metavar` conciso e documente `choices` no `help`.
- Validação no parser: use `pathlib.Path` ou funções conversoras com `ArgumentTypeError` no parâmetro `type=` (ex.: data ISO, formato de arquivo).
- Subcomandos: sempre defina `dest=`, `metavar=` e `required=True`. Use _parent parsers_ com `add_help=False` para compartilhar argumentos comuns.
- Desempenho de CLI: `--help` deve responder em menos de 100ms; adie _imports_ pesados para dentro das funções de execução.
- Escrita de streams e JSONL/CSV: sem auto-flush parcial no meio de linhas; executar `flush()` explícito após cada registro completo para suportar retomada em coletas _append-only_.
- I/O e persistência: crie diretórios intermediários antes de salvar (`pathlib.Path.parent.mkdir(parents=True, exist_ok=True)`); CSVs exclusivamente com `csv.DictWriter` e `fieldnames` explícitos.
- Sinais e subprocessos: capture `KeyboardInterrupt` explicitamente para _cleanup_ e saia com código 130; chamadas a executáveis externos via `subprocess.run` com `capture_output=True`, `check=True` e `timeout=` explícito.
- Relatórios de exploração de dados devem ficar em `docs/exploracao/<dataset>.md`, gerados por scripts em `scripts/`. Metadados brutos volumosos e binários ficam em `data/` fora do Git.
- TODOs devem explicar a lacuna e o motivo; não use TODO como substituto para uma decisão já tomada.

## Git e documentação

- Commits são atômicos por intenção coesa. Separe refatoração preparatória, mudança funcional e correção descoberta durante refatoração.
- Escreva assunto de commit em PT-BR, no presente do indicativo e descrevendo a mudança conceitual: `Adiciona`, `Corrige`, `Extrai`. Use _backticks_ para identificadores de código quando útil.
- Não use `git add .`; revise os arquivos que entram no commit. Execute os testes e o lint aplicáveis antes de concluir.
- Atualize o README quando comandos, fontes, cobertura temporal ou formato de saída mudarem. Se encontrar uma suposição errada neste arquivo, proponha sua correção.
