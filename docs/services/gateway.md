# Gateway

O gateway é a entrada HTTP da loja. Roteia chamadas para os cinco serviços internos, valida a autenticação com o auth e substitui qualquer `id-account` enviado pelo cliente pela identidade obtida de `POST /auth/solve`. Usa Java 25, Spring Boot e Spring Cloud Gateway WebFlux.

## Endpoints e autenticação

| Método e caminho | Destino e comportamento |
|---|---|
| `GET /gateway/health-check` | O próprio gateway responde 200, sem corpo e sem autenticação |
| `/auth/**` | auth; cadastro, login, logout e renovação de token são abertos |
| `/accounts/**` | account; exige token e restringe o acesso à própria conta |
| `/products/**` | product; exige token |
| `/orders/**` | order; exige token |
| `/exchanges/**` ou `/exchange/**` | exchange; exige token |
| `/auth/solve` e `/accounts/login` | Rotas internas: o gateway responde 404 |

O token pode vir de `Authorization: Bearer <token>` ou do cookie HttpOnly `__store_jwt_token`. O refresh token só é aceito no auth. Token ausente ou recusado e falhas na resolução da identidade produzem 401; uma chamada protegida não é encaminhada sem identidade.

## No EKS

O Deployment `gateway` roda no namespace `store`, no cluster `eks-store`, região `us-east-2`. O Service `gateway` é `ClusterIP:8080`; o Service adicional `gateway-public` liga o NLB a esses mesmos pods. É o único serviço de aplicação exposto externamente. `gateway-config` contém os endereços internos e as regras de roteamento.

Startup e liveness usam `/gateway/health-check`. A readiness usa `/actuator/health/readiness` na porta privada 9091; métricas ficam no Service `gateway-metrics`. A configuração inicial tem uma réplica. Durante a demonstração de carga, o [HPA](../load-testing.md) administra de uma a três réplicas.

Depois de configurar o [contexto do EKS](../deployment.md#consultar-o-ambiente), confira:

```bash
kubectl --context eks-store -n store get deploy gateway
kubectl --context eks-store -n store rollout status deploy/gateway
kubectl --context eks-store -n store port-forward svc/gateway 18080:8080
# Em outro terminal:
curl -i http://127.0.0.1:18080/gateway/health-check
```

O [workflow do serviço](https://github.com/projeto-microservicos/gateway-service/blob/main/.github/workflows/ci-cd.yml) testa a alteração e publica no ECR antes do rollout no EKS. O fluxo comum está em [CI/CD](../ci-cd.md).

Fonte: [README do gateway-service](https://github.com/projeto-microservicos/gateway-service). Responsabilidade e assistência de IA: [equipe e autoria](../team.md).
