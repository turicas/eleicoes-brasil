# Contrato efetivo dos artefatos: versão 1

Documento de integração do exportador implementado. A spec de produto em spec/ não é commitada; este contrato descreve o código executável e deve ser lido pelo implementador do app. O frontend nunca busca JSON; URLs de resultado e foto_tse são proveniência, não instrução de chamada pelo navegador.

## Manifesto

Exemplo sintético, sem dados eleitorais reais:

```json
{
  "versao_schema": 1,
  "revisao": "20261005T030000Z-abcdef123456",
  "edicao": {"id": "geral-2026", "ano": 2026, "tipo": "geral"},
  "coletado_em": "2026-10-05T03:00:00+00:00",
  "publicado_em": null,
  "territorios": {
    "BR": "revisoes/20261005T030000Z-abcdef123456/indice.json",
    "AC": "revisoes/20261005T030000Z-abcdef123456/ufs/AC.json"
  }
}
```

Produção normal gera BR + 27 UFs. Caminhos relativos ao prefixo público, sem caminho absoluto/traversal. Revisão identifica exportação, não geração comum do TSE. Publicado_em=null até confirmar upload; não inferir horário remoto. O manifesto só é ativado depois dos artefatos completos; durante upload enviar por último.

## Documento de UF

```json
{
  "versao_schema": 1,
  "revisao": "20261005T030000Z-abcdef123456",
  "edicao": {"id": "geral-2026", "ano": 2026, "tipo": "geral"},
  "territorio": {"tipo": "uf", "codigo": "AC", "nome": "Acre", "uf": "AC"},
  "coletado_em": "2026-10-05T03:00:00+00:00",
  "cargos": [
    {
      "cargo": {"codigo": 3, "nome": "Governador"},
      "abrangencia_disputa": {"tipo": "uf", "codigo": "AC"},
      "eleicao": 6259,
      "turno": 1,
      "vagas": 1,
      "tf": true,
      "md": null,
      "andamento": "f",
      "sem_atribuicao_eleitos": false,
      "motivos": [],
      "estado": "finalizado",
      "fonte": {
        "url": "https://resultados.tse.jus.br/oficial/ele2026/6259/dados/ac/ac-c0003-e006259-u.json",
        "eleicao": 6259,
        "turno": 1,
        "cargo": 3,
        "abrangencia": "AC",
        "gerado_em": "2026-10-05T00:59:00-03:00",
        "totalizado_em": "2026-10-05T00:58:00-03:00",
        "idg": "123",
        "capturado_em": "2026-10-05T03:00:00+00:00",
        "sha256_bruto": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "estado_coleta": "sucesso"
      },
      "eleitos": [
        {
          "sequencial_tse": "123",
          "numero": "10",
          "nome": "Maria José",
          "nome_urna": "MARIA JOSÉ",
          "partido": {"numero": "10", "sigla": "TESTE", "nome": "Partido de teste"},
          "votos": 100,
          "situacao": "Eleito",
          "destinacao_votos": "Válido",
          "foto": {
            "estado": "pendente",
            "url": null,
            "sha256": null,
            "largura": null,
            "altura": null,
            "formato": "webp",
            "fonte_tse": "https://resultados.tse.jus.br/oficial/ele2026/6259/fotos/ac/123.jpeg"
          }
        }
      ]
    }
  ]
}
```

Cargo.estado: pendente, segundo-turno, finalizado ou sem-eleitos. Segundo turno pode estar formalmente totalizado sem eleito; não usar tf=true sozinho para dizer que o titular foi escolhido. Não inferir vencedor da lista vazia ou dos votos. Candidato.e=s sozinho não é eleito. Eleitos ordenados votos decrescentes, nome_urna, sequencial.

Fonte.estado_coleta pode ser ultima-versao-valida, com erro textual adicional, conservando a geração e votos anteriores. Eleitos não finalizados no TSE são lista vazia e estado apropriado; resultado inconsistente gera falha de coleta/normalização, conservando anterior se disponível.

Durante segundo turno pendente, um cargo pode aparecer nos dois turnos; distinguir por código+turno. Quando o segundo turno estiver final, substitui a exibição do primeiro para aquele cargo; outros cargos permanecem do primeiro turno. Não supor que todos os objetos da UF tenham mesmo turno.

Foto disponível: url=fotos/<sha256>.webp, hash SHA-256, largura/altura positivas, formato=webp, estado=disponivel. Falha: estado=erro e URL null; sem mapa: pendente. Não há crop/padding no JSON público. Resolver URL relativa usando o prefixo configurado de data.brasil.io, não o diretório da revisão.

## Índice BR

Mesmo envelope de UF, com territorio BR. cargos contém presidente nacional, se disponível na edição. Campo territorios é lista de objetos {territorio, cargos}; cada cargo resumido contém cargo {codigo,nome}, turno, estado, quantidade_eleitos e gerado_em. Buscar documento completo da UF pelo manifesto, não pelo resumo do índice.

## Mapa de fotos

```json
{
  "versao_schema": 1,
  "fotos": {
    "6259:AC:123": {
      "estado": "disponivel",
      "url": "fotos/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.webp",
      "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "largura": 320,
      "altura": 320,
      "formato": "webp",
      "fonte_tse": "https://resultados.tse.jus.br/oficial/ele2026/6259/fotos/ac/123.jpeg"
    }
  }
}
```

Mapa é entrada do exportador para nova revisão. ZIP contém somente variantes fotos/*.webp, manifesto-fotos.json e erros-fotos.json; não contém originais/estado/modelo. Fotos podem ser publicadas antes dos JSONs sem nova revisão; URLs só ativadas nos documentos com --fotos.

## Validação pelo backend

Aceitar versão 1 e campos extras, rejeitar tipos/contextos/caminhos inválidos. Manter último snapshot válido se refresh falhar. Não interpretar strings da fonte como HTML seguro. Não usar coordenadas de face nem acessar TSE na view. O app não precisa de dependências Pillow/OpenCV, apenas do schema público acima.
