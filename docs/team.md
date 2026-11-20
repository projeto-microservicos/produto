# Equipe e autoria

As responsabilidades abaixo distinguem a implementação inicial das mudanças feitas depois. O uso de IA acompanha a declaração dos READMEs; a responsabilidade pela revisão e entrega continua com os integrantes.

| Pessoa | Período | Contribuição |
|---|---|---|
| `adventurescumm` | Até 16/11/2026 | Implementação inicial de order e exchange; produtor de eventos com outbox/relay; material inicial de carga, HPA e Job de carga |
| João, `joaorcmr` | Desde 17/11/2026 | Gateway, auth, account e product; infraestrutura AWS; integração e operação no EKS |
| João, `joaorcmr` | Desde 17/11/2026 | Evolução de order/exchange: health-checks, consumidor idempotente, DLQ, RabbitMQ no cluster e adaptação PTAX/cache |
| `adventurescumm`, com assistência do Codex | 19/11/2026 | Reorganização desta documentação, páginas dos serviços, estimativa da Calculator, roteiro e slides para revisão do João |
| João, `joaorcmr`, com o Claude | 20/11/2026 | [Front end](services/frontend.md) (React, nginx e rota `/app/**` no gateway); correção da rota `/accounts` no gateway; teste de carga com HPA no EKS |

## Assistência de IA

Os READMEs de gateway, auth, account e product declaram geração de estrutura e regras/testes com Claude por decisão do João, com revisão dele. Order e exchange registram assistência de IA na implementação inicial e nas mudanças posteriores. Os detalhes por arquivo e etapa permanecem nos respectivos repositórios.

O roteiro e os slides organizam a apresentação; não substituem a demonstração real. A gravação e a edição do vídeo, incluindo os trechos do cluster e o link final, pertencem ao João no DOC-04. Os resultados de testes e carga mantêm suas datas e ambientes nas páginas de [validação](validation.md), [mensageria](mensageria.md) e [HPA](load-testing.md).

## Declarações dos serviços

- [Gateway — uso de IA](https://github.com/projeto-microservicos/gateway-service#uso-de-ia)
- [Auth — uso de IA](https://github.com/projeto-microservicos/auth-service#uso-de-ia)
- [Account — uso de IA](https://github.com/projeto-microservicos/account-service#uso-de-ia)
- [Product — uso de IA](https://github.com/projeto-microservicos/product-service#uso-de-ia)
- [Order — autoria e assistência](https://github.com/projeto-microservicos/order-service#attribution-and-assistance)
- [Exchange — repositório e autoria](https://github.com/projeto-microservicos/exchange-service#repositório-e-autoria)
