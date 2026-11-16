# Arquitetura e contratos

O cliente acessa o gateway. O gateway valida o token e define `id-account` com o UUID da conta autenticada, sobrescrevendo qualquer identidade fornecida pelo cliente. Os serviços internos confiam nesse header dentro da rede autorizada.

| Origem | Requisição | Destino e identidade |
|---|---|---|
| Cliente via gateway | `/products/*` | `http://product:8080`; gateway fornece `id-account` |
| Cliente via gateway | `/exchanges/*` | `http://exchange:8080`; gateway fornece `id-account` |
| order | `GET /products/{id}` | `http://product:8080`; repassa `id-account` |
| order | `GET /exchanges/USD/{currency}` | `http://exchange:8080`; repassa `id-account` |

As chamadas internas não precisam retornar ao gateway. Os nomes DNS curtos pressupõem Services no mesmo namespace. Rotas de account, auth e order devem ser documentadas conforme a implementação do gateway; não são inferidas dos contratos acima.

## Produto e câmbio consumidos por order

Produto retorna um objeto JSON com `id` e `price`, sendo o preço monetário em USD não negativo. O order usa o preço do serviço, sem aceitar totais enviados pelo cliente.

```json
{"id":"00000000-0000-0000-0000-000000000001","price":10.12}
```

Câmbio retorna JSON com `sell` positivo. O campo `buy` também pode ser retornado; order usa a cotação de venda para converter USD na moeda solicitada.

```json
{"sell":6.00,"buy":5.90}
```

O contrato consumido por order trata produto inexistente como 404 no provedor e moeda não suportada como 422 no provedor. Falhas de dependência resultam em 503 na API de pedidos. Esses comportamentos precisam ser verificados em integração com as implementações reais.

## API de pedidos

| Método e caminho | Comportamento |
|---|---|
| `POST /orders` | Cria pedido com preços consultados; retorna 201 |
| `GET /orders` | Lista pedidos da conta atual |
| `GET /orders/{id}` | Detalhes em USD; pedido de outra conta retorna 404 |
| `GET /orders/{id}?currency=BRL` | Converte a resposta sem alterar valores persistidos |

```json
{"items":[{"idProduct":"00000000-0000-0000-0000-000000000001","quantity":2}]}
```

O serviço de pedidos persiste seus dados no schema `orders` do PostgreSQL. Seu build não inclui o código dos provedores HTTP.
