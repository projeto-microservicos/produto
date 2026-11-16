# Custos e responsabilidades

## Inventário e estimativa do projeto

Consulta de 16/11/2026 na conta do projeto, região Ohio (`us-east-2`): EKS `eks-store` ativo, versão 1.37, dois nós `t2.small`, dois discos gp3 de 20 GiB, dois NAT Gateways, pelo menos três IPv4 públicos e nenhum RDS ou balanceador ELBv2. Apenas auth e gateway estão implantados. O script `python scripts/capture-aws.py` refaz as consultas sem ler Secrets e salva inventário e preços unitários em `artifacts/aws-inventory.local.json`.

Estimativa em USD, 730 horas/mês, On-Demand, sem créditos, impostos ou câmbio:

| Recurso existente | Cálculo mensal | USD/mês |
|---|---|---:|
| Control plane EKS, suporte padrão | 1 × 730 × 0,10 | 73,00 |
| Dois nós Linux t2.small | 2 × 730 × 0,023 | 33,58 |
| Discos gp3 dos nós | 40 GiB × 0,08 | 3,20 |
| Dois NAT Gateways, parcela fixa | 2 × 730 × 0,045 | 65,70 |
| Três IPv4 públicos observados, mínimo | 3 × 730 × 0,005 | 10,95 |
| **Subtotal dos itens acima** | | **186,43** |

O subtotal não é a fatura total: faltam ECR, tráfego de saída e entre zonas, processamento de dados nos NATs, CloudWatch e outros recursos não inventariados. Os dois NATs também cobram US$ 0,045 por GB processado. O HPA não reduz o custo fixo do EKS nem dos nós já provisionados. Os preços de EC2, NAT e armazenamento foram consultados pela API oficial AWS Price List; EKS e IPv4 seguem as páginas oficiais [EKS Pricing](https://aws.amazon.com/eks/pricing/) e [VPC Pricing](https://aws.amazon.com/vpc/pricing/).

Proposta preparada, **não executada por decisão do usuário**:

| Adição | Configuração | USD/mês estimado |
|---|---|---:|
| PostgreSQL gerenciado | RDS db.t4g.micro, Single-AZ, 730h | 11,68 |
| Disco do RDS | gp3, 20 GiB | 2,30 |
| Terceiro nó | EC2 t2.small, 730h | 16,79 |
| Disco do terceiro nó | gp3, 20 GiB | 1,60 |
| **Subtotal adicional** | Sem Secrets Manager, APIs e possível IPv4 extra | **32,37** |

Planeje uma margem para chegar a aproximadamente US$ 35–40/mês adicionais. Dimensionar três nós é uma proposta inicial, sujeita ao consumo medido e aos limites de pods por nó. Para uma sessão curta, horas de computação são proporcionais ao tempo ligado; discos, snapshots, NATs, Secrets e demais recursos têm seus próprios ciclos de cobrança. Remover pods não remove esses recursos. O template de RDS retém um snapshot quando o banco é excluído, e esse snapshot pode continuar cobrando armazenamento.

## Entrega na AWS Pricing Calculator

O [exercício de custos](https://insper.github.io/platform/pt/2026.2/exercises/project/costs/#custos) exige uma estimativa na calculadora AWS. A planilha `aws/cost-plan.csv` registra as entradas e premissas. Na [AWS Pricing Calculator](https://calculator.aws/), crie uma estimativa em **US East (Ohio)** e cadastre EKS, EC2 Linux com gp3, VPC/NAT e IPv4. Inclua RDS PostgreSQL Single-AZ no cenário proposto, além de ECR, CloudWatch e tráfego com o consumo esperado.

Salve dois cenários: **existente** e **proposto com RDS e capacidade para HPA**. Exporte PDF/CSV e guarde o link compartilhável na entrega. Esta revisão fornece os parâmetros e preços da API; ainda é necessário salvar a estimativa na interface da calculadora. Anexe também o período de uso real consultado no Cost Explorer para comparar estimativa e consumo. Créditos estudantis alteram o valor a pagar, não o custo bruto do serviço.

## Onde utilizamos PaaS e serviços gerenciados

O EKS existente já fornece o plano de controle Kubernetes gerenciado: a AWS opera esse plano de controle e a equipe define imagens, Deployments, requests/limits, probes e escalonamento. Descreva-o como plataforma Kubernetes gerenciada/CaaS. Os nós EC2 continuam sob responsabilidade da equipe; Redis, RabbitMQ ou PostgreSQL em containers não se tornam serviços gerenciados por rodarem nesse cluster.

O RDS é a demonstração proposta de banco gerenciado/DBaaS, frequentemente tratado dentro de PaaS: a AWS cuida da infraestrutura do banco, backups e manutenção configurada, enquanto a equipe cuida de usuários, schemas, migrações, consultas e acesso. `aws/rds.yaml` prepara PostgreSQL privado em duas sub-redes, acesso 5432 apenas a partir dos nós EKS, criptografia e senha administrativa no Secrets Manager. **Não afirmar que o grupo já utiliza RDS: ele não foi criado nesta etapa.**

Na apresentação, mostre o EKS real e seus Deployments; explique as responsabilidades de cada parte. Quando o RDS for autorizado e utilizado, mostre o estado disponível, configuração privada, conexão da aplicação e migrações Flyway nos schemas `accounts`, `products` e `orders`, sem expor credenciais. A classificação deve seguir a terminologia adotada pelo professor; não apresente EC2 isolada como PaaS. Fontes: [EKS](https://aws.amazon.com/eks/), [responsabilidade compartilhada no RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.html), [RDS PostgreSQL Pricing](https://aws.amazon.com/rds/postgresql/pricing/).

## Decisão de operação

O usuário escolheu manter a AWS preparada, sem criar recursos ou ampliar os nós, e usar port-forward. Não foram criados RDS, balanceadores, DNS, novas instâncias, Secrets Manager ou orçamento AWS. Os recursos que já estavam ativos continuam sujeitos à cobrança da conta. Não remova NATs ou outros componentes de rede sem avaliar as rotas e dependências do cluster.

As faturas seguem a conta ou organização que hospeda o recurso. O rateio entre integrantes depende de um acordo da equipe; criar um workflow não define quem deve pagar ao grupo.

| Recurso | Quem recebe a cobrança | Condição |
|---|---|---|
| Repositório GitHub e submodules | Titular/organização, conforme o plano | Submodules são referências Git e não exigem um serviço pago próprio |
| MkDocs | Não exige serviço hospedado pago próprio | Gera arquivos estáticos localmente ou no CI |
| GitHub Pages | Titular/organização do repositório | Disponível para repositórios públicos no GitHub Free; repositórios privados exigem plano compatível |
| GitHub Actions | Titular/organização do repositório | Runners padrão são gratuitos em repositórios públicos; em privados há franquias e eventual cobrança; armazenamento tem regras próprias |
| EKS, nós, discos e rede | Conta AWS que hospeda os recursos | Cobrança continua enquanto existirem recursos faturáveis |
| ECR | Conta AWS do registro | Armazenamento e outros consumos seguem a tabela do serviço |
| RDS | Conta AWS do banco | Provisionar somente após aprovação do responsável |
| Redis/RabbitMQ no cluster | Conta AWS do cluster | Consomem CPU, memória e eventualmente discos/rede; podem exigir mais nós |

Para documentação pública, use o domínio padrão `github.io` e runners padrão do Actions. Não é necessário contratar EC2, S3 ou RDS para servir o MkDocs no Pages. Domínio próprio e planos pagos são decisões separadas.

O responsável pela conta AWS aprova RDS e qualquer aumento de capacidade. A equipe deve combinar previamente orçamento, eventual rateio e data de desligamento dos recursos. Não há valor mensal fixado aqui: ele depende de região, tipos/tamanhos, horas, armazenamento e rede.

Fontes oficiais consultadas em 16/11/2026:

- [GitHub Pages e planos suportados](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Cobrança do GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Preços do EKS e recursos associados](https://aws.amazon.com/eks/pricing/)
- [Preços do ECR](https://aws.amazon.com/ecr/pricing/)
- [Preços do RDS](https://aws.amazon.com/rds/pricing/)
