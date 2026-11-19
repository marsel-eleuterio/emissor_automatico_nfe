# Comparativo de extratores

Rodada mais recente de cada extrator. Campos críticos marcados com *.

| Campo | `claude-code:haiku` | `claude-code:sonnet` | `ollama:gemma4:12b:sem-pensar` | `oraculo` | `regex` |
| --- | --- | --- | --- | --- | --- |
| extracao: banco_codigo | 24/24 | 23/24 | 23/24 | 24/24 | 21/24 |
| extracao: banco_conta | 24/24 | 23/24 | 23/24 | 24/24 | 19/24 |
| extracao: descricao_texto * | 21/24 | 21/24 | 19/24 | 24/24 | 3/24 |
| extracao: descricao_tipo | 23/24 | 23/24 | 23/24 | 24/24 | 3/24 |
| extracao: local_prestacao * | 24/24 | 24/24 | 24/24 | 24/24 | 22/24 |
| extracao: n_pedidos | 22/22 | 22/22 | 22/22 | 22/22 | 20/22 |
| extracao: prazo_envio | 22/22 | 22/22 | 21/22 | 22/22 | 22/22 |
| extracao: tipo_documento | 23/24 | 24/24 | 24/24 | 24/24 | 22/24 |
| extracao: tomador_doc * | 21/24 | 24/24 | 21/24 | 24/24 | 22/24 |
| extracao: valor * | 24/24 | 24/24 | 24/24 | 24/24 | 18/24 |
| extracao: vencimento | 23/24 | 24/24 | 21/24 | 24/24 | 16/24 |
| nota: banco_no_corpo | 24/24 | 23/24 | 23/24 | 24/24 | 8/22 |
| nota: cliente_identificado | 24/24 | 24/24 | 24/24 | 24/24 | 24/24 |
| nota: cod_trib_nacional | 23/24 | 23/24 | 23/24 | 23/24 | 21/22 |
| nota: descricao_nucleo * | 21/24 | 21/24 | 21/24 | 23/24 | 0/22 |
| nota: lei_12741_valor | 17/24 | 17/24 | 17/24 | 17/24 | 14/22 |
| nota: municipio_incidencia * | 24/24 | 24/24 | 24/24 | 24/24 | 22/22 |
| nota: nota_composta | — | — | — | — | 0/2 |
| nota: texto_irrf | 24/24 | 24/24 | 24/24 | 24/24 | 22/22 |
| nota: tomador_doc * | 19/24 | 22/24 | 19/24 | 22/24 | 20/22 |
| nota: valor * | 22/24 | 22/24 | 22/24 | 22/24 | 17/22 |
| **Total** | **449/476** | **454/476** | **442/476** | **463/476** | **336/462** |
