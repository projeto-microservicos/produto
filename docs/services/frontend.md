# Front end

A loja tem uma interface web, a **Quitanda**, publicada pelo próprio gateway:

**<http://a488cbb85e8304108b4f9563359cf260-811be60b7d8b4e24.elb.us-east-2.amazonaws.com/app/>**

O endereço raiz (`/`) redireciona para `/app/`.

É um SPA em React 19, TypeScript e Vite, servido por nginx sem root. O gateway encaminha `/app/**` para o Service `frontend`. Assim, a página e a API têm a mesma origem: não há CORS, segundo endereço público nem segundo balanceador.

## Telas

| Tela | O que mostra | Chamadas pelo gateway |
|---|---|---|
| Entrar | Login e cadastro | `POST /auth/login`, `POST /auth/register`, `GET /auth/me` |
| Catálogo | Cada produto como um cartaz de preço em dólar, busca por nome, cadastro e remoção. A sacola soma em USD e fecha o pedido | `GET/POST/DELETE /products`, `POST /orders` |
| Pedidos | Lista dos pedidos da conta e o cupom de cada um, na moeda escolhida, com a taxa PTAX usada e se ela veio do cache | `GET /orders`, `GET /orders/{id}?currency=`, `GET /exchange/USD/{moeda}` |
| Câmbio | Conversor entre as 11 moedas, com venda, compra, boletim, origem (`X-Cache`) e tempo de resposta | `GET /exchange/{de}/{para}` |
| Sistema | O health-check de cada serviço pelo gateway, a cada 15 s, e o caminho de uma requisição | `GET /<serviço>/health-check` |
| Conta | Dados da conta, sair e apagar | `POST /auth/logout`, `DELETE /accounts/{id}` |

## Rotas no gateway

| Rota | Comportamento |
|---|---|
| `GET /` | 302 para `/app/` |
| `GET /app/**` | Aberta: só HTML, JS e CSS. Encaminhada ao Service `frontend` sem `id-account` |
| `POST`, `PUT`, `DELETE` em `/app/**` | 401, como qualquer rota protegida sem token |

Cada chamada que a página faz à API passa pelas mesmas regras de antes: token obrigatório, identidade resolvida no auth e regra de dono em cada serviço.

## Sessão no navegador

O auth devolve o par de tokens no corpo e em cookies HttpOnly marcados `Secure`.

- **HTTPS ou `localhost`:** o navegador guarda os cookies, e a página não armazena nenhum token.
- **HTTP puro, como no NLB:** o navegador descarta cookies `Secure`. O token de acesso fica só em memória e o de renovação no `sessionStorage` da aba, e as chamadas usam `Authorization: Bearer`. Um TLS no NLB (ACM e um domínio) devolveria o modo de cookies; ficou fora por custo e prazo.

Um 401 dispara uma única renovação em `POST /auth/refresh` e repete a chamada. Se a renovação falhar, a página volta para a tela de entrada.

## No EKS

| Item | Valor |
|---|---|
| Deployment e Service | `frontend` no namespace `store`; Service `ClusterIP:8080` |
| Imagem | `frontend-service` no ECR, fixada por digest |
| Health-check | `GET /app/health-check` (200 sem corpo) nas probes de startup, liveness e readiness |
| Recursos | 10m de CPU e 24 MiB reservados; limite de 200m e 64 MiB |
| Segurança | uid 101, FS somente leitura (só `/tmp` gravável), sem capabilities, sem token de service account |
| Cabeçalhos | CSP com `connect-src 'self'`, `nosniff`, `no-referrer` e `X-Frame-Options: DENY` |

```bash
kubectl --context eks-store -n store get deploy,svc frontend
curl -i http://<DNS do NLB>/app/health-check
```

A imagem é publicada à mão (`docker buildx --platform linux/amd64` e push no ECR) e aplicada com `kubectl apply -f k8s/k8s.yaml`. O CI do repositório confere tipos, build e imagem; o deploy automático, como nos outros serviços, exigiria incluir o ECR `frontend-service` na política IAM do CI e um RBAC próprio.

## Desenvolvimento local

```bash
npm ci
npm run dev   # http://localhost:5173/app/, com proxy da API para o NLB
STORE_GATEWAY_URL=http://localhost:8080 npm run dev   # contra o gateway do Compose
```

Fonte: [README do frontend-service](https://github.com/projeto-microservicos/frontend-service), também em `services/frontend` como submodule. Escrito pelo agente do João (Claude) em 20/11/2026, a pedido dele; ver [equipe e autoria](../team.md).
