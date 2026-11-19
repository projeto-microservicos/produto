# Order

O order registra pedidos e seus preços no schema `orders` do PostgreSQL. Consulta product e exchange por HTTP em tempo de execução; não incorpora o código desses serviços no build. Usa Java 25 e Spring Boot. A confirmação assíncrona de pedidos é o [gargalo de mensageria escolhido](../mensageria.md).

## Endpoints

| Método e caminho | Comportamento |
|---|---|
| `POST /orders` | Recebe itens com `idProduct` e `quantity`; calcula os valores e responde 201 |
| `GET /orders` | Lista resumos dos pedidos da conta autenticada |
| `GET /orders/{id}` | Detalha o pedido em USD; outro dono ou pedido inexistente retorna 404 |
| `GET /orders/{id}?currency=BRL` | Converte a resposta com a cotação de venda, sem alterar os dados em USD |
| `GET /orders/health-check` | 200 sem corpo; não exige token nem `id-account` no serviço |

O gateway fornece `id-account`. Produto inexistente gera 400 na criação; moeda não suportada retorna 422; falha de dependência retorna 503. O serviço consulta o preço e não aceita um total calculado pelo cliente. Não existe `DELETE /orders`.

```json
{"items":[{"idProduct":"UUID_DO_PRODUTO","quantity":2}]}
```

JWT próprio de order, pagamentos e cache Redis são recursos opcionais; não fazem parte do fluxo básico da demonstração. A autenticação desse fluxo fica no gateway.

## No EKS

`order` roda com uma réplica no namespace `store`, cluster `eks-store`, em `us-east-2`, atrás do Service `ClusterIP:8080`. Usa `order-config`, `order-secrets` e seu usuário/schema no RDS privado. Os destinos internos são `http://product:8080` e `http://exchange:8080`.

`MESSAGING_ENABLED=true` e `ORDER_WORKER_ENABLED=true` ligam a outbox, o relay e o consumidor de confirmação. O RabbitMQ é interno ao cluster. O cache Redis permanece desligado. O pedido e o evento são gravados na mesma transação; falhas de publicação são tentadas novamente, e o consumidor deduplica por `eventId`.

Startup e liveness usam `/orders/health-check`. Readiness usa `/actuator/health/readiness` na porta privada 9091; métricas ficam no Service `order-metrics`. O rollout usa `maxSurge=0` e pode interromper brevemente a única réplica.

Com o [contexto configurado](../deployment.md#consultar-o-ambiente):

```bash
kubectl --context eks-store -n store rollout status deploy/order
kubectl --context eks-store -n store port-forward svc/order 18082:8080
# Em outro terminal:
curl -i http://127.0.0.1:18082/orders/health-check
```

O [workflow do order](https://github.com/projeto-microservicos/order-service/blob/main/.github/workflows/ci-cd.yml) publica por digest e só faz release/deploy quando as respectivas condições estão habilitadas; veja [CI/CD](../ci-cd.md).

Fonte: [README do order-service](https://github.com/projeto-microservicos/order-service). Responsabilidade e assistência de IA: [equipe e autoria](../team.md).
