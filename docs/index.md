# Projeto de microsserviços

O projeto separa account, auth, gateway, product, exchange e order em repositórios independentes. Este agregador registra os commits usados em conjunto e centraliza os contratos e a operação.

| Serviço | Responsabilidade | Situação informada pela equipe |
|---|---|---|
| account | Contas | Esqueleto no EKS; lógica pendente |
| auth | Autenticação e tokens | Esqueleto no EKS; lógica pendente |
| gateway | Entrada, validação do token e identidade da conta | Esqueleto no EKS; contrato de rotas definido |
| product | Consulta de produtos e preços | Repositório confirmado; deploy a confirmar |
| exchange | Cotações entre moedas | Implementação e pipelines publicadas; deploy AWS depende de configuração |
| order | Pedidos, totais e conversão | Implementação e CI/CD publicados; deploy AWS depende de configuração |

O contrato está acordado; isso não comprova que os endpoints já estejam funcionais no cluster. O PostgreSQL/RDS aguarda autorização do responsável pela conta. Redis, RabbitMQ e a segunda réplica de order ficam desativados nesta fase por capacidade.

Consulte [arquitetura e contratos](architecture.md), [desenvolvimento](development.md), [deploy e capacidade](deployment.md) e [custos](costs.md).
