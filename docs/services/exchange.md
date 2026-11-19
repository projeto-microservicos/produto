# Exchange

O exchange é uma API Python 3.12 com FastAPI que fornece cotações da PTAX do Banco Central. Calcula taxas cruzadas usando o BRL como referência e guarda cotações por moeda em memória. Não tem banco de dados próprio. O order usa sua cotação de venda para converter a apresentação dos pedidos.

## Endpoints

| Método e caminho | Comportamento |
|---|---|
| `GET /exchanges/{source}/{target}` | Cotação com `sell`, `buy`, `date` e `id-account`; exige o header de identidade |
| `GET /exchange/{source}/{target}` | Alias singular do mesmo contrato |
| `GET /exchange/health-check` | 200 sem corpo; não exige identidade e não consulta o BCB |
| `GET /health` e `GET /ready` | Disponibilidade do processo; `ready` é usado na readiness |
| `GET /metrics` | Métricas Prometheus internas |
| `GET /docs` e `GET /openapi.json` | Documentação interativa e schema da API interna |

As moedas aceitas são AUD, BRL, CAD, CHF, DKK, EUR, GBP, JPY, NOK, SEK e USD. Moeda fora dessa lista ou `id-account` ausente/inválido retorna 422. Moedas iguais retornam 1 sem chamar o BCB. Falha do provedor sem cotação disponível retorna 503.

O boletim mais recente disponível é guardado por cinco minutos. Requisições concorrentes compartilham a consulta por moeda. Se o BCB falhar e houver cotação vencida, o serviço pode devolvê-la com `X-Cache: stale`, aguardando 30 segundos para tentar novamente. `X-Cache: hit` indica uso de cache e `miss` indica consulta ao provedor. A PTAX não é um feed de mercado em tempo real.

O adaptador de fechamento em `app/bacen.py` permanece no repositório com seus testes; a API usa `app/ptax.py`, que seleciona o boletim mais recente. A identidade da conta é acrescentada a cada resposta e não é compartilhada no cache.

## No EKS

O Deployment `exchange` roda com uma réplica no namespace `store`, cluster `eks-store`, em `us-east-2`. O Service `exchange` é `ClusterIP:8080`, e a configuração vem de `exchange-config`. A saída HTTPS para o BCB usa a rede do cluster; não existe entrada pública direta.

Startup e liveness usam `/exchange/health-check`; readiness usa `/ready`, todos na porta 8080. `CACHE_ENABLED=false` desliga apenas o Redis opcional: o cache em memória continua ativo. `MESSAGING_ENABLED=false` desliga os eventos opcionais de telemetria `QuoteFetched`.

Com o [contexto configurado](../deployment.md#consultar-o-ambiente):

```bash
kubectl --context eks-store -n store rollout status deploy/exchange
kubectl --context eks-store -n store port-forward svc/exchange 18084:8080
# Em outro terminal:
curl -i http://127.0.0.1:18084/exchange/health-check
```

Não direcione carga de demonstração ao BCB: use o health-check do gateway ou USD/USD, conforme [teste de carga](../load-testing.md). O [workflow do exchange](https://github.com/projeto-microservicos/exchange-service/blob/main/.github/workflows/ci-cd.yml) testa e publica com OIDC; veja [CI/CD](../ci-cd.md).

Fonte: [README do exchange-service](https://github.com/projeto-microservicos/exchange-service). Responsabilidade e assistência de IA: [equipe e autoria](../team.md).
