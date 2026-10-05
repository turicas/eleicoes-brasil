# Exportadores dos eleitos

Pacote independente da apuração no Sheets. Não importa nem altera `apuracao/`, não
usa Google nem envia dados ao MinIO. Resultados vêm do EA20 oficial; só entram as
situações `Eleito`, `Eleito por QP` e `Eleito por média`, com totalização final.
Segundo turno não é eleito. Fotos prontas são WebP quadradas; crop e padding ficam
somente no estado local.

## Resultados

Na raiz do repositório, com as dependências HTTP já existentes:

```bash
python -m portal_eleitos.exportar 2026 data/portal-eleitos --workers 6
```

Saída: `data/portal-eleitos/publicacao/manifesto.json`, índice BR e documentos das
27 UFs em revisões imutáveis. `brutos/` fica separado e não deve ser publicado.
Cada execução gera nova revisão; o manifesto só muda depois de todos os documentos
serem gravados. Fonte indisponível conserva a última versão válida, com diagnóstico;
sem versão anterior, não ativa revisão incompleta. Resposta antiga ou regressão de
finalização não apaga eleitos; exige revisão humana. No segundo turno, cargos do
primeiro são conservados e a disputa pendente é incluída sem duplicação:

```bash
python -m portal_eleitos.exportar 2026 data/portal-eleitos --turno 2
```

Só funciona quando o segundo turno estiver explicitamente publicado no EA11.
Não calcula quocientes, não atribui eleito por votos, nem tenta furar o cache do
CDN com garantia. `coletado_em` é horário local da exportação; cada cargo tem geração
oficial própria e hash do bruto.

## Fotos: ambiente separado

Use ambiente separado para não mexer no processo da planilha:

```bash
python -m venv .venv-fotos-eleitos
. .venv-fotos-eleitos/bin/activate
python -m pip install -r portal_eleitos/requirements-fotos.txt
```

Modelo YuNet para OpenCV 4.x, versão 2023mar (232.589 bytes), SHA-256 confirmado
na validação desta implementação:

```bash
mkdir -p data/portal-eleitos/modelo
curl --fail --location --connect-timeout 5 --max-time 30 \
    https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx \
    -o data/portal-eleitos/modelo/face_detection_yunet_2023mar.onnx
printf '%s  %s\n' \
    8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4 \
    data/portal-eleitos/modelo/face_detection_yunet_2023mar.onnx | sha256sum --check
```

Não prossiga se o hash divergir. O arquivo do modelo não é versionado aqui;
licença e referência: https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet .

```bash
python -m portal_eleitos.fotos \
    data/portal-eleitos/publicacao/manifesto.json \
    data/portal-eleitos/fotos-processadas \
    data/portal-eleitos/modelo/face_detection_yunet_2023mar.onnx \
    --workers 4
```

Rodar o mesmo comando retoma por fonte/modelo/parâmetros e hash dos arquivos;
Ctrl+C sai 130, preservando registros concluídos. Estado JSONL é append-only,
com flush por item. Versão de parâmetros/modelo ou override novo invalida somente
a variante pertinente e reutiliza o original válido.

Saídas:

- `fotos/*.webp`: 320x320, qualidade 85, margem de rosto 0,45; parâmetros modificáveis.
- `mapa-fotos.json`: campos públicos da foto por `eleicao:UF:sequencial_tse`, sem coordenadas faciais.
- `estado-fotos.jsonl`: auditoria local incluindo detecção, padding e erros.
- `originais/`: imagens originais, não publicar.
- `fotos.zip`: variantes individuais, manifesto de fotos e relatório de erros.

Detector roda localmente em CPU com uma thread interna por worker. Sem face
confiável, múltiplas faces ou erro de inferência: contain conservador e registro
para revisão. Não há reconhecimento de identidade. Overrides opcionais em JSON:

```json
{
  "6259:AC:123": {"x": 10, "y": 15, "largura": 180, "altura": 180}
}
```

A janela deve ser quadrada, em pixels da imagem orientada. Use `--overrides ARQUIVO`.
Erros por foto não bloqueiam as demais; verifique `erros-fotos.json` dentro do ZIP
ou registros locais. A CLI retorna 1 se há fotos com erro. Uma folha de contato
para revisão em lote não está implementada nesta entrega; pode-se abrir as WebP
individualmente. O enquadramento automático precisa de revisão, principalmente
para fotos com iluminação/pessoas/enquadramentos incomuns.

Incorporar o mapa numa nova revisão dos JSONs:

```bash
python -m portal_eleitos.exportar 2026 data/portal-eleitos --somente-fotos \
    --fotos data/portal-eleitos/fotos-processadas/mapa-fotos.json
```

`--somente-fotos` clona a revisão ativa sem refazer HTTP ao TSE. Sem essa opção,
`--fotos` pode acompanhar uma coleta nova. Isso não sobrescreve JSONs de revisões
anteriores. Fotos ausentes no mapa continuam
pendentes. URLs disponíveis pressupõem upload dos arquivos antes do manifesto;
não publicar manifesto que aponta para arquivos ainda não enviados.

## Upload manual MinIO

Cliente `mc` com alias já configurado, sem chaves na linha de comando. Confirme
alias/bucket/endpoint: o domínio público data.brasil.io não prova o endpoint S3.
Não alterar permissões nem apagar revisões.

```bash
export DESTINO='ALIAS/BUCKET/eleicoes/2026/resultados'
export REVISAO="$(python -c 'import json; from pathlib import Path; print(json.loads(Path("data/portal-eleitos/publicacao/manifesto.json").read_text())["revisao"])')"

mc cp --recursive \
    --attr 'Content-Type=image/webp;Cache-Control=public,max-age=31536000,immutable' \
    data/portal-eleitos/fotos-processadas/fotos/ "$DESTINO/fotos/"

mc cp --recursive \
    --attr 'Content-Type=application/json;Cache-Control=public,max-age=31536000,immutable' \
    "data/portal-eleitos/publicacao/revisoes/$REVISAO/" "$DESTINO/revisoes/$REVISAO/"
```

Conferir arquivos e hashes por URL pública. Só depois enviar o manifesto:

```bash
mc cp --attr 'Content-Type=application/json;Cache-Control=no-cache,max-age=0,must-revalidate' \
    data/portal-eleitos/publicacao/manifesto.json "$DESTINO/manifesto.json"
```

`publicado_em` permanece null até a publicação remota ser confirmada, não inventa
horário de upload. O ZIP não é extraído pelo MinIO; os comandos acima enviam os
arquivos individuais. Não publicar brutos, originais, estado ou modelos. Depois
executar o comando de atualização de cache a ser implementado no Brasil.IO.

## Contrato e integração

`manifesto.json`: `versao_schema=1`, `revisao`, `edicao`, `coletado_em`,
`publicado_em`, `territorios` (BR/UF -> caminho relativo da revisão).

Documentos de UF: contexto territorial, edição, coleta, cargos com status e
proveniência, lista completa `eleitos`, partido e foto. Índice BR: mesmos campos
principais e resumo de cargos por território, além do cargo presidencial nacional.
`foto.fonte_tse` é proveniência para o exportador local, não src da imagem no HTML.
URL de foto pronta é relativa ao prefixo (`fotos/hash.webp`).

TODO: migrar a normalização transitória para a biblioteca `eleicoes` quando sua API
pública existir; não introduzir dependência do repositório inteiro no Brasil.IO.

Testes sintéticos e focados:

```bash
python -m pytest portal_eleitos -o addopts='' -q
```

Nenhuma fixture contém retratos reais. Para executar os testes de imagem, instalar
as dependências de fotos no ambiente de teste. Código gera dados em diretórios
locais fora do Git; não exporta número de documento ou data de nascimento.
