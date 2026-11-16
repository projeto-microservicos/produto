# Deploy e capacidade

Cada serviço mantém Dockerfile, `k8s/k8s.yaml` e `.github/workflows/ci-cd.yml` em seu próprio repositório. O responsável pela AWS cria os repositórios ECR e libera acesso ao EKS para as roles de deploy. Este agregador não cria infraestrutura.

## Release de order

O CI executa testes Java, testes dos scripts, scan Trivy, build Docker e validação de Compose. A publicação no ECR usa credenciais temporárias via GitHub OIDC e o deploy usa digest de imagem. PRs não recebem a identidade AWS de release.

No [repositório de order](https://github.com/projeto-microservicos/order-service), configure `AWS_REGION`, `AWS_ACCOUNT_ID`, `AWS_ROLE_ARN`, `ECR_REPOSITORY`, `EKS_CLUSTER_NAME`, `K8S_NAMESPACE` e `KUBECTL_VERSION`. O [guia completo de implantação](https://github.com/projeto-microservicos/order-service/blob/main/docs/GITHUB-ACTIONS-EKS.md) acompanha a migração já publicada. O [exchange](https://github.com/projeto-microservicos/exchange-service/blob/main/docs/DEPLOYMENT.md) também fornece GitHub Actions com OIDC e uma pipeline Jenkins alternativa.

- `RELEASE_ENABLED=true`: publica a cada push em `main` depois da validação.
- `DEPLOY_ENABLED=false`: publica sem acessar o cluster, enquanto o banco aguarda liberação.
- Execução manual em `main`: a opção `deploy` controla aquele deploy e começa desmarcada.

OIDC precisa de trust policy restrita ao repositório/branch, permissões ECR, `eks:DescribeCluster`, acesso EKS e RBAC no namespace. Um endpoint EKS privado também exige conectividade do runner à VPC.

## Restrições atuais

| Recurso | Configuração atual |
|---|---|
| order | Uma réplica; sem Pod adicional durante atualização |
| Redis/cache | Desligado no Deployment |
| RabbitMQ/mensageria | Desligado no Deployment |
| HPA de order | Não aplicar enquanto a capacidade for insuficiente |
| PostgreSQL/RDS | Obrigatório para executar order; aguarda autorização |
| Serviços | Internos, por ClusterIP; entrada autenticada pelo gateway |

Com uma réplica e `maxSurge=0`, o rollout pode causar indisponibilidade breve. Se já existir HPA, o responsável deve removê-lo ou ajustá-lo antes de usar essa configuração.

Quando houver capacidade, Redis e RabbitMQ serão instalados no próprio cluster, com armazenamento, credenciais e limites definidos. ElastiCache e Amazon MQ não fazem parte desta etapa. A segunda réplica e o HPA também exigem capacidade aprovada.

ConfigMaps e Secrets são preparados separadamente e não são sobrescritos pelo release. Não versione senhas, tokens, kubeconfigs ou arquivos locais de ambiente. O pipeline não provisiona RDS e não dispensa a dependência de PostgreSQL.
