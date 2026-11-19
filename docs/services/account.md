# Account

O account mantém as contas no schema `accounts` do PostgreSQL. Normaliza e-mails, impede duplicatas e guarda apenas o hash BCrypt da senha. O auth usa sua API interna para cadastro e verificação de credenciais. Usa Java 25 e Spring Boot.

## Endpoints

| Método e caminho | Comportamento |
|---|---|
| `POST /accounts` | Cria conta e responde 201 com `Location`; corpo com nome, e-mail e senha |
| `GET /accounts` | Pelo gateway, retorna apenas a conta autenticada; uso interno pode listar todas |
| `GET /accounts/{id}` | 200 com a conta; inexistente ou pertencente a outra pessoa retorna 404 |
| `DELETE /accounts/{id}` | 204; a mesma regra de propriedade se aplica |
| `POST /accounts/login` | Interno: confere e-mail e senha; erro retorna 401 |
| `GET /accounts/health-check` | 200 sem corpo; disponível diretamente ao Kubernetes, sem token |

Senhas precisam ter ao menos oito caracteres e no máximo 72 bytes UTF-8. E-mail repetido retorna 409; dados inválidos retornam 400. O login responde 401 tanto para conta desconhecida quanto para senha errada. Pelo gateway, `id-account` é sempre obtido do token; o cliente não escolhe a identidade. `/accounts/login` fica bloqueado no gateway com 404.

## No EKS

`account` roda com uma réplica no namespace `store` do EKS `eks-store`, em `us-east-2`. Seu Service é `ClusterIP:8080`. `account-config` fornece a configuração não sensível; `account-secrets` fornece as credenciais. O RDS é privado e compartilhado com product e order, com usuários e schemas separados. O Flyway administra as tabelas do serviço.

Startup e liveness chamam `/accounts/health-check`. Readiness fica em `/actuator/health/readiness`, na porta privada 9091, e as métricas são acessadas pelo Service `account-metrics`.

Com o [contexto configurado](../deployment.md#consultar-o-ambiente):

```bash
kubectl --context eks-store -n store rollout status deploy/account
kubectl --context eks-store -n store port-forward svc/account 18083:8080
# Em outro terminal:
curl -i http://127.0.0.1:18083/accounts/health-check
```

O health-check verifica o atendimento HTTP; ele não substitui a readiness nem comprova acesso ao banco. Publicação de imagem e rollout são feitos pelo [workflow do account](https://github.com/projeto-microservicos/account-service/blob/main/.github/workflows/ci-cd.yml), descrito em [CI/CD](../ci-cd.md).

Fonte: [README do account-service](https://github.com/projeto-microservicos/account-service). Responsabilidade e assistência de IA: [equipe e autoria](../team.md).
