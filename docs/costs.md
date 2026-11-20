# Custos, PaaS e SLA

Levantamento de **17/11/2026** na conta AWS do projeto, região **US East (Ohio), `us-east-2`**. Os preços são on-demand, consultados na [AWS Price List API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/price-changes.html), e o mês tem 730 horas. Os valores estão em USD, sem créditos estudantis. Os impostos aparecem à parte: no Cost Explorer, eles ficaram em cerca de 13,9% sobre o uso.

## Resumo

| | USD |
|---|---:|
| Gasto real de 1 a 17/11, Cost Explorer, com impostos | **39,59** |
| Custo mensal projetado com a infra de 17/11, sem impostos | **242,65** |
| Mesmo valor por dia | ~7,98 |
| Custo mensal projetado com impostos (~13,9%) | ~276 |

O cluster existe desde 12/11. Até 16/11, o gasto ficou em ~US$ 6,13 por dia. Desde 17/11, entraram o RDS, o NLB e o 3º nó, e o ritmo passa para ~US$ 8 por dia, antes dos impostos.

## Gasto real (Cost Explorer)

De 1 a 17/11/2026. O dia 17 está parcial e o RDS e o NLB ainda não aparecem, porque o Cost Explorer atrasa cerca de 24 h.

| Serviço | USD |
|---|---:|
| EKS (plano de controle) | 13,60 |
| EC2 - Other (NAT 12,33; EBS gp3 0,59; tráfego 0,03) | 12,95 |
| EC2 - Compute (nós t2.small) | 6,16 |
| VPC (IPv4 públicos) | 2,04 |
| ECR, S3, SNS, CloudFormation, Cost Explorer | 0,01 |
| Impostos | 4,82 |
| **Total** | **39,59** |

## Plano de custos

### Infraestrutura em uso (17/11)

| Recurso | Configuração | Preço unitário | USD/mês |
|---|---|---|---:|
| EKS `eks-store` | plano de controle, suporte padrão | 0,10/h | 73,00 |
| Nós do cluster | 3× EC2 t2.small, Linux | 0,023/h cada | 50,37 |
| Discos dos nós | 3× 20 GiB gp3 | 0,08/GB-mês | 4,80 |
| NAT Gateways | 2 (um por AZ) | 0,045/h cada, mais 0,045/GB processado | 65,70 |
| Network Load Balancer | `gateway-public`, único ponto de entrada | 0,0225/h, mais 0,006/LCU-h | 16,43 |
| IPv4 públicos | 5 (2 dos NATs, 2 do NLB, 1 de um nó) | 0,005/h cada | 18,25 |
| RDS PostgreSQL | db.t4g.micro, Single-AZ | 0,016/h | 11,68 |
| Disco do RDS | 20 GiB gp3 | 0,115/GB-mês | 2,30 |
| ECR | 6 repositórios, ~1,2 GB de imagens, até 20 imagens por repositório | 0,10/GB-mês | 0,12 |
| **Total** | | | **242,65** |

Ficam de fora o tráfego variável (processamento dos NATs, LCUs do NLB, saída para a internet) e o backup do RDS, que não é cobrado enquanto não passar do tamanho do banco. No uso do projeto, esses itens somaram centavos.

### Para onde vai o dinheiro

- **Rede (NAT e IPv4), ~35%:** é o maior item, e não roda nenhuma aplicação. Os dois NATs dão redundância entre as zonas de disponibilidade.
- **EKS, 30%:** o preço fixo do plano de controle gerenciado, igual para qualquer tamanho de cluster.
- **Computação, 23%:** 3 nós pequenos para 6 serviços, o RabbitMQ e as réplicas do HPA.
- **Banco gerenciado, 6%:** um RDS compartilhado, com um schema e um usuário por serviço, sai mais barato que um banco por serviço.

### Cenários

| Cenário | Variação mensal | Total/mês |
|---|---:|---:|
| Infra de 17/11 (acima) | — | 242,65 |
| RabbitMQ dentro do cluster (`emptyDir`) | 0, cabe nos 3 nós | 242,65 |
| 4º nó para o HPA do teste de carga | +16,79 de EC2 e +1,60 de disco | 261,04 |
| Nós desligados das 23:59 às 06:00 (usado de 17 a 19/11) | −12,59, só o EC2 dos nós; os discos continuam | 230,06 |
| 1 NAT em vez de 2, sem redundância entre AZs | −32,85 | 209,80 |
| Nós só em subnets privadas, sem o IPv4 do nó | −3,65 | 239,00 |
| RDS Multi-AZ, para o SLA de 99,95% | +11,68 de instância e +2,30 de disco | 256,63 |

**O desligamento noturno economizou pouco.** De 17 a 19/11, um agendamento no Auto Scaling Group zerava os 3 nós das 23:59 às 06:00 (`infra/scheduler/nos-noturno.sh`). Eram 6 de 24 horas do EC2 dos nós: ~US$ 0,41 por noite, ~US$ 12,59 por mês, **cerca de 5% da conta**. O resto não para à noite: EKS, NATs, NLB, IPv4 e RDS (~77% do total) cobram por hora, com ou sem nó. Para economizar de verdade, seria preciso tirar o segundo NAT (−13,5%) ou desligar o ambiente inteiro fora das avaliações. Em 20/11, dia da entrega, o agendamento foi removido para o sistema ficar no ar o tempo todo.

### Controle e encerramento

- Todos os recursos criados para o projeto levam a tag `Project=plataformas-store`, para filtrar no Cost Explorer.
- Um orçamento mensal no **AWS Budgets**, com alerta por e-mail, está previsto para limitar surpresas.
- **Depois da nota**, desligar na ordem: NLB, RDS (snapshot final opcional, que também cobra armazenamento), node group, cluster EKS e NATs. Remover pods não para a cobrança: a conta vem dos recursos AWS, não das aplicações.

### Estimativa na AWS Pricing Calculator

O enunciado pede a estimativa na [AWS Pricing Calculator](https://calculator.aws/). As entradas são as da tabela de infraestrutura em uso, todas em **US East (Ohio)**:

- **Amazon EKS:** 1 cluster.
- **Amazon EC2:** 3× t2.small Linux, on-demand, 730 h, 20 GB gp3 cada.
- **Amazon VPC:** 2 NAT Gateways, 5 IPv4 públicos e ~1 GB por mês processado.
- **Elastic Load Balancing:** 1 NLB.
- **Amazon RDS for PostgreSQL:** db.t4g.micro, Single-AZ, 20 GB gp3.
- **Amazon ECR:** 1,2 GB.

**[Abrir a estimativa pública salva em 19/11/2026](https://calculator.aws/#/estimate?id=8694ae17668ebc72f35152c53c51a062a77c80b7).** O total é **US$ 242,70/mês**, sem impostos, **US$ 0,05 acima** dos US$ 242,65 do plano. A pequena diferença vem do processamento de 1 GB/mês nos NATs, da hipótese adicional de 1 GB de tráfego TCP por mês no NLB e dos arredondamentos por serviço da Calculator.

O tráfego dos NATs foi dividido em 0,5 GB por gateway. Para o NLB, a hipótese de 1 GB/mês permite estimar o componente variável exigido pela Calculator; não é uma medição de uso. A comparação mantém 730 h/mês, sem descontar a agenda noturna dos nós, créditos ou impostos. Não inclui RDS Proxy, suporte estendido do PostgreSQL, Database Insights pago ou suporte AWS adicional.

[Baixar as premissas e os totais conferidos (JSON)](assets/aws-pricing-estimate.json).

## Onde usamos PaaS

PaaS (*Platform as a Service*) é quando o provedor opera a plataforma e a equipe só cuida da aplicação e da configuração. No projeto, cada serviço gerenciado tira uma parte da operação da equipe:

| Serviço | Modelo | O que o provedor opera | O que a equipe faz |
|---|---|---|---|
| **Amazon EKS** | Kubernetes gerenciado (CaaS) | Plano de controle (API server, etcd, upgrades, alta disponibilidade entre AZs) | Manifests, probes, requests/limits, RBAC, HPA, Secrets e ConfigMaps |
| **Amazon RDS for PostgreSQL** | Banco gerenciado (DBaaS, uma forma de PaaS) | Instalação, patches do PostgreSQL, backups automáticos, criptografia em repouso, TLS obrigatório | Um usuário e um schema por serviço (account, product, order), migrations com Flyway, acesso só a partir dos nós |
| **Amazon ECR** | Registro de imagens gerenciado | Armazenamento, disponibilidade, scan de vulnerabilidades no push | Imagens imutáveis, deploy por digest, retenção de 20 imagens |
| **Elastic Load Balancing (NLB)** | Balanceador gerenciado | Alta disponibilidade, escala, IPs públicos | Expor só o gateway; os outros serviços ficam em ClusterIP |
| **GitHub Actions** | CI/CD como serviço | Runners, filas, logs | Workflows de teste, build, scan e deploy no EKS por OIDC, sem chave AWS guardada |
| **GitHub Pages** | Hospedagem estática | Servir o site com HTTPS | O MkDocs gera o site, publicado pelo workflow `docs.yml` |

Ficam de fora do PaaS os nós EC2 e a rede (VPC, subnets, NAT), que são IaaS: a AWS cuida do hardware, mas o sistema operacional e a capacidade são da equipe. O mesmo vale para o RabbitMQ: rodar dentro do cluster não o torna gerenciado, e a operação dele (dados, atualização, recuperação) é da equipe. O Amazon MQ seria a alternativa gerenciada; ficou de fora por custo (mq.t3.micro a US$ 0,027/h, ~US$ 20/mês mais o disco, para um broker que cabe nos nós existentes).

## SLA

Compromissos de disponibilidade mensal publicados pela AWS, consultados em 17/11/2026. São compromissos com crédito em caso de falha, não garantias.

| Serviço | Compromisso | Escopo |
|---|---:|---|
| [Amazon EKS](https://aws.amazon.com/eks/sla/) | 99,95% | Endpoint da API do cluster (plano de controle padrão) |
| [Amazon EC2](https://aws.amazon.com/compute/sla/) | 99,5% por instância; 99,99% por região | Instância isolada; ou instâncias em 2 ou mais AZs |
| [Amazon RDS](https://aws.amazon.com/rds/sla/) | 99,5% Single-AZ; 99,95% Multi-AZ | Por instância |
| [Elastic Load Balancing](https://aws.amazon.com/elasticloadbalancing/sla/) | 99,99% | Balanceador em 2 ou mais AZs (o nosso NLB está em 2) |
| [Amazon ECR](https://aws.amazon.com/ecr/sla/) | 99,9% | Por região |
| [NAT Gateway](https://aws.amazon.com/vpc/sla/) | 99,9% | Por NAT Gateway |
| [GitHub Actions](https://github.com/customer-terms/github-online-services-sla) | 99,9% | Para clientes pagantes; o crédito é sobre o valor pago. A org usa o plano Free, então não há compensação |

### SLA composto

Uma requisição só funciona se todos os componentes no caminho dela estiverem de pé, então as disponibilidades se multiplicam. Hoje cada serviço tem **1 réplica**, e por isso vale o SLA por instância do EC2 (99,5%). A conta considera o pior caso, com cada serviço num nó diferente. O plano de controle do EKS e o ECR não estão no caminho da requisição: uma falha neles impede deploys e escalonamento, não o atendimento.

| Caminho | Componentes | Disponibilidade | Indisponibilidade permitida por mês |
|---|---|---:|---:|
| `GET /products` | NLB × nó do gateway × nó do product × RDS | 0,9999 × 0,995³ = **98,50%** | ~11 h |
| `POST /orders` | o mesmo, mais o nó do order | 0,9999 × 0,995⁴ = **98,01%** | ~14,6 h |
| `GET /orders/{id}?currency=BRL` | o mesmo, mais o nó do exchange e o NAT | 0,9999 × 0,995⁵ × 0,999 = **97,42%** | ~18,9 h |

O provedor de câmbio externo não tem SLA, então o último caminho, na prática, fica abaixo disso.

**Como melhorar:**

- Com **2 réplicas de cada serviço em AZs diferentes**, a computação passa a valer o SLA regional (99,99%). O `GET /products` sobe para 0,9999 × 0,9999 × 0,995 = **99,48%** (~3,8 h por mês), e o RDS Single-AZ vira o elo fraco. As réplicas dobram os requests de memória, o que pede o 4º nó (cenário acima).
- Com o **RDS Multi-AZ**, o mesmo caminho chega a **99,93%** (~0,5 h por mês), por +US$ 14 por mês.
- Os nós já estão em 2 AZs (us-east-2a e us-east-2b). Falta só subir as réplicas, o que o HPA faz sob carga.

## Responsabilidades de cobrança

| Recurso | Quem recebe a cobrança |
|---|---|
| EKS, EC2, EBS, NAT, IPv4, NLB, RDS, ECR | A conta AWS do projeto |
| GitHub (repositórios, Actions, Pages) | A organização `projeto-microservicos`, no plano Free: repositórios públicos não pagam Actions nos runners padrão nem Pages |

## Fontes

- [Preços do EKS](https://aws.amazon.com/eks/pricing/), [EC2](https://aws.amazon.com/ec2/pricing/on-demand/), [VPC/NAT e IPv4](https://aws.amazon.com/vpc/pricing/), [ELB](https://aws.amazon.com/elasticloadbalancing/pricing/), [RDS for PostgreSQL](https://aws.amazon.com/rds/postgresql/pricing/), [ECR](https://aws.amazon.com/ecr/pricing/)
- [SLAs da AWS](https://aws.amazon.com/legal/service-level-agreements/) e o [SLA dos serviços online do GitHub](https://github.com/customer-terms/github-online-services-sla)
- [Cobrança do GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
