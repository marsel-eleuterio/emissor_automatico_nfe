# Comparativo de extratores

Rodada mais recente de cada extrator. Campos críticos marcados com *.

| Campo | `claude-code:haiku` | `claude-code:sonnet` | `oai:gemini:gemini-3.1-flash-lite` | `oai:gemini:gemini-3.5-flash-lite` | `oai:gemini:gemini-3.8-flash` | `ollama:gemma4:12b:pensando` | `ollama:gemma4:12b:sem-pensar` | `ollama:qwen3.5:9b:pensando` | `ollama:qwen3.5:9b:sem-pensar` | `ollama:qwen3:14b:pensando` | `ollama:qwen3:14b:sem-pensar` | `oraculo` | `regex` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| extracao: banco_codigo | 6/6 | 6/6 | 5/6 | 6/6 | 1/6 | 4/6 | 5/6 | 1/6 | 2/6 | 5/6 | 4/6 | 6/6 | 6/6 |
| extracao: banco_conta | 6/6 | 6/6 | 5/6 | 6/6 | 1/6 | 4/6 | 5/6 | 1/6 | 2/6 | 5/6 | 4/6 | 6/6 | 6/6 |
| extracao: descricao_texto * | 6/6 | 6/6 | 3/6 | 5/6 | 1/6 | 2/6 | 5/6 | 1/6 | 5/6 | 5/6 | 5/6 | 6/6 | 4/6 |
| extracao: descricao_tipo | 6/6 | 6/6 | 5/6 | 5/6 | 1/6 | 2/6 | 3/6 | 0/6 | 1/6 | 2/6 | 2/6 | 6/6 | 4/6 |
| extracao: itens_produto | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 | 1/1 | 0/1 |
| extracao: local_prestacao * | 6/6 | 6/6 | 5/6 | 6/6 | 1/6 | 4/6 | 6/6 | 1/6 | 6/6 | 6/6 | 6/6 | 6/6 | 4/6 |
| extracao: n_pedidos | 5/5 | 5/5 | 5/5 | 5/5 | 1/5 | 4/5 | 5/5 | 1/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| extracao: prazo_envio | 5/5 | 5/5 | 5/5 | 5/5 | 3/5 | 4/5 | 4/5 | 3/5 | 5/5 | 3/5 | 5/5 | 5/5 | 5/5 |
| extracao: tipo_documento | 6/6 | 6/6 | 6/6 | 6/6 | 1/6 | 4/6 | 6/6 | 1/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| extracao: tomador_doc * | 6/6 | 6/6 | 6/6 | 6/6 | 1/6 | 4/6 | 6/6 | 1/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| extracao: valor * | 6/6 | 6/6 | 6/6 | 6/6 | 1/6 | 4/6 | 6/6 | 1/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| extracao: vencimento | 6/6 | 6/6 | 6/6 | 6/6 | 1/6 | 3/6 | 4/6 | 1/6 | 6/6 | 3/6 | 6/6 | 6/6 | 6/6 |
| nota: banco_no_corpo | 5/5 | 5/5 | 4/5 | 5/5 | 1/1 | 3/3 | 4/5 | 1/1 | 1/5 | 4/5 | 4/5 | 5/5 | 4/5 |
| nota: cliente_identificado | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| nota: cod_trib_nacional | 5/5 | 5/5 | 5/5 | 5/5 | 1/1 | 3/3 | 5/5 | 1/1 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| nota: descricao_nucleo * | 5/5 | 5/5 | 5/5 | 5/5 | 1/1 | 2/3 | 5/5 | 1/1 | 5/5 | 5/5 | 5/5 | 5/5 | 3/5 |
| nota: lei_12741_valor | 5/5 | 5/5 | 5/5 | 5/5 | 1/1 | 3/3 | 5/5 | 1/1 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| nota: municipio_incidencia * | 5/5 | 5/5 | 5/5 | 5/5 | 1/1 | 3/3 | 5/5 | 1/1 | 5/5 | 5/5 | 5/5 | 5/5 | 3/5 |
| nota: nota_composta | — | — | — | — | 0/5 | 0/2 | — | 0/5 | — | — | — | — | — |
| nota: produto_catalogo | 1/1 | 1/1 | 0/1 | 0/1 | — | 0/1 | 0/1 | — | 0/1 | 0/1 | 0/1 | 1/1 | 0/1 |
| nota: texto_irrf | 5/5 | 5/5 | 5/5 | 5/5 | 1/1 | 3/3 | 5/5 | 1/1 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| nota: tomador_doc * | 6/6 | 6/6 | 6/6 | 6/6 | 1/1 | 4/4 | 6/6 | 1/1 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| nota: valor * | 6/6 | 6/6 | 6/6 | 6/6 | 1/1 | 4/4 | 6/6 | 1/1 | 5/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| **Total** | **114/114** | **114/114** | **105/114** | **111/114** | **27/84** | **71/100** | **103/114** | **26/84** | **93/114** | **99/114** | **102/114** | **114/114** | **101/114** |
