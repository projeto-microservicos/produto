# Deploy e capacidade

## Destino confirmado e decisão desta etapa

O destino é o EKS `eks-store`, conta `533267095490`, região `us-east-2`, namespace `store`. Em 16/11/2026 o usuário escolheu **deixar AWS preparada, sem novos gastos**, com acesso via **port-forward**. Os comandos de criação ou aplicação abaixo são um roteiro futuro e não foram executados. Não há RDS disponível; apenas auth e gateway estão no cluster. O template RDS passou pela validação da API CloudFormation, sem criar stack.

O node group `default` tem dois nós `t2.small`. As seis aplicações pedem 750m CPU e 1.920 MiB de memória, antes dos componentes do sistema; duas réplicas extras de gateway acrescentam 200m/640 MiB. O consumo real pode superar os requests. A proposta é avaliar um terceiro nó e medir antes de aplicar HPA. [Custos e premissas](costs.md).

Se a ampliação for autorizada futuramente, o comando preparado é:

```bash
aws eks update-nodegroup-config --cluster-name eks-store --nodegroup-name default --scaling-config minSize=1,maxSize=10,desiredSize=3 --region us-east-2
aws eks wait nodegroup-active --cluster-name eks-store --nodegroup-name default --region us-east-2
kubectl --context arn:aws:eks:us-east-2:533267095490:cluster/eks-store get nodes
```

Espere o terceiro nó ficar `Ready` e confirme a capacidade disponível antes de implantar. Esses comandos não foram executados. Reduzir de volta para dois nós exige antes verificar se as aplicações restantes cabem nessa capacidade.

## Preparação do banco gerenciado, quando autorizada

O arquivo `aws/rds.yaml` prepara um PostgreSQL RDS privado, Single-AZ, db.t4g.micro e 20 GiB gp3. Usa as sub-redes privadas nas duas zonas existentes e libera PostgreSQL somente para o security group dos nós. A senha master é gerenciada pelo Secrets Manager. O arquivo `aws/rds-parameters.example.json` contém os identificadores observados nessa VPC; confirme-os antes de criar.

```bash
# Apenas valida; não cria recurso
aws cloudformation validate-template --template-body file://aws/rds.yaml --region us-east-2

# Somente após autorizar os novos custos
aws cloudformation create-stack --stack-name store-database --template-body file://aws/rds.yaml --parameters file://aws/rds-parameters.example.json --region us-east-2
aws cloudformation wait stack-create-complete --stack-name store-database --region us-east-2
aws cloudformation describe-stacks --stack-name store-database --region us-east-2 --query 'Stacks[0].Outputs'
```

Copie `aws/environment.example.json` para `aws/environment.local.json` e preencha `database_host` com o output `Endpoint`. O `cors_origin` padrão é o loopback usado pelo port-forward, sem depender de domínio. O arquivo não recebe senhas. Para preparar usuários separados e schemas `accounts`, `products` e `orders`, use o output `MasterSecretArn`:

```bash
.venv/Scripts/python.exe scripts/configure-database.py --environment aws/environment.local.json --admin-secret-arn ARN_DO_MASTER_SECRET
```

Esse comando lê a credencial master e grava o plano sensível em `.local/`, sem exibi-la. Não altera o cluster. Após revisar o destino, repetir com `--apply` executa um Job temporário dentro do EKS, cria um usuário por serviço, aplica os Secrets correspondentes e remove o Job e o Secret master temporários. As senhas de aplicação ficam preservadas para novas execuções. O login da aplicação não usa o usuário master. Flyway cria as tabelas dentro de cada schema. Não rode esse bootstrap sobre dados existentes de outro usuário sem revisar ownership e permissões.

A identidade usada nessa preparação precisa de acesso ao CloudFormation/RDS/rede para criar a stack, `secretsmanager:GetSecretValue` para ler a credencial master e RBAC para Secrets/Jobs no namespace. As permissões de release ECR/EKS existentes podem não incluir esse bootstrap; a criação efetiva e essas permissões ainda não foram testadas nesta etapa.

`auth-secrets` já existe no EKS. O deploy verifica apenas se contém `JWT_SECRET`, sem ler o valor. Se precisar criar em outro namespace, gere uma chave aleatória de pelo menos 32 bytes em um arquivo local ignorado e use `kubectl create secret generic auth-secrets --from-env-file=...` no contexto e namespace explícitos. Não use `.env` local como configuração de produção.

## Publicar as imagens e implantar

Primeiro conclua os testes locais. Imagens locais são `store/{serviço}-service:dev`, construídas pelo Compose da raiz. A publicação exige AWS CLI, Docker e acesso ECR:

```bash
.venv/Scripts/python.exe scripts/publish-images.py --environment aws/environment.local.json --create-repositories
.venv/Scripts/python.exe scripts/render-eks.py --environment aws/environment.local.json --images artifacts/images.local.json
.venv/Scripts/python.exe scripts/deploy-eks.py --environment aws/environment.local.json
```

O primeiro comando publica seis imagens com tag única e registra seus digests; `--create-repositories` cria o repositório de exchange, ausente na consulta, e quaisquer outros faltantes. A publicação também usa armazenamento ECR faturável e não foi executada nesta etapa. O login ECR é temporário e não altera as credenciais Docker persistentes. O renderer gera ConfigMaps e Deployments com imagens por digest, SSL no PostgreSQL, sem criar banco, HPA ou entrada pública.

O último comando verifica conta, contexto explícito, chaves dos Secrets e executa `--dry-run=server`; somente a opção adicional `--apply` altera as aplicações. Antes de aplicar, confirme espaço com `kubectl top nodes` e `kubectl describe nodes`. A aplicação completa ainda depende de RDS e capacidade. Os serviços continuam ClusterIP, e cache/mensageria de order/exchange permanecem desligados.

```bash
# Apenas depois de resolver as dependências e revisar o manifesto
.venv/Scripts/python.exe scripts/deploy-eks.py --environment aws/environment.local.json --apply

# Terminal 1: acesso ao gateway, sem criar Load Balancer
kubectl --context arn:aws:eks:us-east-2:533267095490:cluster/eks-store -n store port-forward svc/gateway 18080:8080

# Terminal 2: teste pelo túnel
python scripts/smoke.py --base-url http://127.0.0.1:18080
```

O túnel existe enquanto o terminal estiver aberto e não publica uma URL acessível pela internet. A exposição pública com HTTPS é uma etapa separada. Não aplique o `public.example.yaml` HTTP para enviar credenciais.

O script salva os Deployments anteriores em `artifacts/previous-deployments.local.yaml`. Para reverter uma versão de um serviço, use `kubectl --context CONTEXTO_EKS -n store rollout undo deployment/NOME` e acompanhe o rollout. Serviços criados pela primeira vez não terão revisão anterior. O rollout atual sem surge pode interromper brevemente uma aplicação de réplica única.

As alterações locais em account, auth, gateway, product e a normalização dos scripts de order precisam ser commitadas nos próprios repositórios; publique esses commits antes de atualizar os gitlinks do agregador. Os pipelines existentes continuam sendo a opção para releases recorrentes. Este roteiro permite validar um conjunto de imagens localmente antes de publicar.

Cada serviço mantém Dockerfile, `k8s/k8s.yaml` e `.github/workflows/ci-cd.yml` em seu próprio repositório. O responsável pela AWS cria os repositórios ECR e libera acesso ao EKS para as roles de deploy. A preparação de infraestrutura pelo template deste agregador é uma etapa separada dos pipelines dos serviços.

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
