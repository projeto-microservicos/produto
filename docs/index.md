# Projeto de microsserviços

O projeto separa account, auth, gateway, product, exchange e order em repositórios independentes. Este agregador registra os commits usados em conjunto e centraliza os contratos e a operação.

| Serviço | Responsabilidade | Situação informada pela equipe |
|---|---|---|
| account | Contas | Lógica e testes implementados localmente; não implantado no EKS |
| auth | Autenticação e tokens | Lógica e testes implementados localmente; EKS ainda usa versão anterior |
| gateway | Entrada, validação do token e identidade da conta | Validação implementada localmente; EKS ainda usa versão anterior |
| product | Consulta de produtos e preços | CRUD e testes implementados localmente; não implantado no EKS |
| exchange | Cotações entre moedas | Implementação e pipelines publicadas; deploy AWS depende de configuração |
| order | Pedidos, totais e conversão | Implementação e CI/CD publicados; deploy AWS depende de configuração |

O Compose da raiz reúne os seis serviços para validação local. As alterações nos submodules ainda precisam ser publicadas nos repositórios correspondentes. O EKS `eks-store`, em `us-east-2`, tem dois nós `t2.small`, Metrics Server e versões anteriores de auth/gateway. Em 16/11/2026 o usuário escolheu manter AWS preparada, sem novos gastos, com acesso previsto por port-forward. RDS e ampliação de capacidade não foram executados. Redis, RabbitMQ e a segunda réplica de order ficam desativados nesta fase.

Consulte [arquitetura e contratos](architecture.md), [desenvolvimento](development.md), [carga e HPA](load-testing.md), [deploy e capacidade](deployment.md) e [custos](costs.md).
