# Auth

O auth cadastra contas por meio do account, confere credenciais e emite um par de tokens JWT: um access token de curta duração e um refresh token. Também resolve a identidade consultada pelo gateway. Usa Java 25 e Spring Boot e não tem banco próprio.

## Endpoints

| Método e caminho | Resposta e uso |
|---|---|
| `POST /auth/register` | 201 com a conta; validação delegada ao account; e-mail repetido retorna 409 |
| `POST /auth/login` | 200 com `token`, `refreshToken`, `tokenType` e `expiresIn`, além dos cookies HttpOnly |
| `POST /auth/refresh` | 200 com um novo par; recebe o refresh token no cookie ou no corpo |
| `POST /auth/logout` | 204; expira os dois cookies |
| `GET /auth/me` | 200 com a conta identificada pelo gateway |
| `POST /auth/solve` | Interno: retorna `idAccount` para um access token válido; inválido retorna 401 |
| `GET /auth/health-check` | 200 sem corpo; não depende do account nem exige token no serviço |

Cadastro, login, refresh e logout são abertos no gateway. `/auth/solve` não é exposto por ele. O claim `token_use` separa access e refresh; uma conta excluída não pode renovar. Os tempos padrão são 15 minutos e sete dias, respectivamente. O logout limpa os cookies, mas um token copiado continua válido até expirar; revogação imediata exigiria estado adicional.

## No EKS

O Deployment `auth` e o Service `auth` (`ClusterIP:8080`) ficam no namespace `store`, cluster `eks-store`, em `us-east-2`. Uma réplica recebe a configuração de `auth-config` e o segredo de assinatura de `auth-secrets`. O endereço do account é interno, `http://account:8080`; o serviço não acessa o RDS diretamente.

Startup e liveness chamam `/auth/health-check`. Readiness e Prometheus usam a porta privada 9091, por `/actuator/health/readiness` e pelo Service `auth-metrics`.

Com o [contexto configurado](../deployment.md#consultar-o-ambiente):

```bash
kubectl --context eks-store -n store rollout status deploy/auth
kubectl --context eks-store -n store port-forward svc/auth 18081:8080
# Em outro terminal:
curl -i http://127.0.0.1:18081/auth/health-check
```

Os cookies são HttpOnly e têm configuração de `Secure` e `SameSite`. Não publique a chave JWT no repositório. A imagem é publicada no ECR e implantada pelo [workflow do auth](https://github.com/projeto-microservicos/auth-service/blob/main/.github/workflows/ci-cd.yml), com [OIDC](../ci-cd.md).

Fonte: [README do auth-service](https://github.com/projeto-microservicos/auth-service). Responsabilidade e assistência de IA: [equipe e autoria](../team.md).
