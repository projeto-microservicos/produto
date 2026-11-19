# Product

O product mantém o catálogo e os preços em USD no schema `products` do PostgreSQL. O order consulta o produto por HTTP para calcular o preço de cada pedido. Usa Java 25 e Spring Boot e tem build independente dos demais serviços.

## Endpoints

| Método e caminho | Comportamento |
|---|---|
| `POST /products` | Cria produto com nome, preço e unidade; responde 201 com `Location` |
| `GET /products` | Lista produtos em ordem de nome |
| `GET /products?name=tom` | Filtra pelo trecho do nome, sem diferenciar maiúsculas |
| `GET /products/{id}` | Retorna o produto; inexistente retorna 404 |
| `DELETE /products/{id}` | Exclui e responde 204; inexistente retorna 404 |
| `GET /products/health-check` | 200 sem corpo; não exige token diretamente no serviço |

O preço precisa ser maior que zero, com no máximo duas casas decimais. Nome e unidade são aparados. Dados inválidos retornam 400. O gateway exige autenticação para as rotas de produto. Papéis de administrador para criar e excluir não fazem parte da implementação atual. Pedidos guardam uma cópia do preço, portanto excluir o produto não altera os pedidos anteriores.

## No EKS

O Deployment `product` roda com uma réplica no namespace `store`, cluster `eks-store`, em `us-east-2`. O Service `product` é `ClusterIP:8080`. `product-config` e `product-secrets` fornecem configuração e credenciais. O usuário do RDS é dono do schema `products`, separado dos schemas de account e order; a conexão usa TLS e o Flyway aplica as migrations.

Startup e liveness chamam `/products/health-check`. A readiness usa `/actuator/health/readiness` na porta privada 9091; o Service `product-metrics` expõe as métricas internamente.

Com o [contexto configurado](../deployment.md#consultar-o-ambiente):

```bash
kubectl --context eks-store -n store rollout status deploy/product
kubectl --context eks-store -n store port-forward svc/product 18085:8080
# Em outro terminal:
curl -i http://127.0.0.1:18085/products/health-check
```

O order usa `http://product:8080` dentro do namespace. O [workflow do product](https://github.com/projeto-microservicos/product-service/blob/main/.github/workflows/ci-cd.yml) testa, publica no ECR e atualiza o Deployment conforme o [fluxo de CI/CD](../ci-cd.md). O repositório do produto é privado; seus links exigem acesso à organização.

Fonte: [README do product-service](https://github.com/projeto-microservicos/product-service). Responsabilidade e assistência de IA: [equipe e autoria](../team.md).
