# De onde vem cada campo da nota

Checagem automática: o valor que está na nota aparece no texto do pedido?

| Campo | A1 | B1 | C1 | C2 | D1 | E1 |
| --- | --- | --- | --- | --- | --- | --- |
| Tomador: CNPJ/CPF | email | email | email | email | email | email |
| Tomador: nome | email | email | email | email | email | email |
| Tomador: CEP | email | consulta | email | email | email | email |
| Tomador: bairro | email | email | email | email | consulta | consulta |
| Valor | email | email | email | email | email | email |
| Prestador (quem emite) | remetente ou assunto | email | email | email | email | remetente ou assunto |
| Descrição do serviço | email + cadastro | email | email | email | email | — |
| Código de serviço | cadastro | cadastro | cadastro (pista no email) | cadastro (pista no email) | cadastro | — |
| Município de incidência do ISS | regra | regra | email + regra | email + regra | regra | — |
| Conta bancária no corpo | cadastro | email | email | email | email | — |
| Valor aprox. de tributos (Lei 12.741) | cadastro (alíquota do mês) | cadastro (alíquota do mês) | cadastro (alíquota do mês) | cadastro (alíquota do mês) | cadastro (alíquota do mês) | — |
| Texto de dispensa de IRRF | — | — | cadastro | cadastro | — | — |
| Competência | regra | regra | regra | regra | regra | — |
| Produto (código, NCM, CFOP) | — | — | — | — | — | cadastro (catálogo) |
| Quantidade e preço | — | — | — | — | — | email |
