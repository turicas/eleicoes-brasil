# Exportação dos eleitos

O exportador lê as fontes oficiais do TSE, preserva os brutos por hash e produz revisões imutáveis dos resultados com um manifesto de publicação.

```bash
python -m portal_eleitos.exportar 2026 data/portal-eleitos
```

A identificação dos eleitos usa os estados publicados pelo TSE, sem calcular quocientes ou atribuir eleição pela votação. Falhas de atualização preservam a última versão válida. O manifesto é atualizado somente após os documentos da revisão estarem gravados.

O formato dos documentos e sua proveniência estão descritos em [contrato.md](contrato.md).
