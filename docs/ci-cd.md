# CI/CD

Cada serviço é testado, empacotado e implantado pelo seu próprio **GitHub Actions**. A imagem vai para o **Amazon ECR** e o Deployment no **EKS** recebe seu digest imutável. O GitHub obtém credenciais AWS temporárias por **OIDC**; não há necessidade de guardar uma chave de acesso AWS permanente no repositório.

## Da alteração ao rollout

```text
pull request → testes e validações → revisão → merge na main
                                                   ↓
                                   OIDC → build → ECR → digest
                                                           ↓
                                              EKS → rollout status
```

PRs validam o código e não recebem a identidade de release AWS. Na `main`, a publicação e o deploy dependem das condições de cada workflow. O código de cada serviço, o Dockerfile e os manifests vivem no mesmo repositório; os submodules do agregador apenas fixam versões usadas em conjunto.

| Repositório | Validação | Publicação e deploy |
|---|---|---|
| [Gateway](https://github.com/projeto-microservicos/gateway-service/blob/main/.github/workflows/ci-cd.yml) | Maven, build de container e Compose | Na `main`, com `AWS_ROLE_ARN` configurada |
| [Auth](https://github.com/projeto-microservicos/auth-service/blob/main/.github/workflows/ci-cd.yml) | Maven, build de container e Compose | Na `main`, com `AWS_ROLE_ARN` configurada |
| [Account](https://github.com/projeto-microservicos/account-service/blob/main/.github/workflows/ci-cd.yml) | Maven, build de container e Compose | Na `main`, com `AWS_ROLE_ARN` configurada |
| [Product](https://github.com/projeto-microservicos/product-service/blob/main/.github/workflows/ci-cd.yml) | Maven, build de container e Compose | Na `main`, com `AWS_ROLE_ARN` configurada |
| [Order](https://github.com/projeto-microservicos/order-service/blob/main/.github/workflows/ci-cd.yml) | Maven, testes dos scripts, scan, container e Compose | Push na `main` com `RELEASE_ENABLED=true`; deploy automático também exige `DEPLOY_ENABLED=true` |
| [Exchange](https://github.com/projeto-microservicos/exchange-service/blob/main/.github/workflows/ci-cd.yml) | Pytest, testes dos scripts, auditoria, Redis/RabbitMQ, container e Compose | Mesmas condições de release/deploy de order |

Order e exchange também oferecem execução manual a partir da `main`, com uma opção explícita de deploy. O valor padrão dessa opção é desligado. Portanto, um merge publica e implanta automaticamente quando as variáveis e permissões necessárias estão habilitadas; a presença do arquivo de workflow, isoladamente, não garante isso.

## Por que Actions, ECR e OIDC

| Decisão | Motivo no projeto |
|---|---|
| GitHub Actions | O código e as revisões já estão no GitHub; a execução fica registrada por commit e dispensa administrar um servidor Jenkins |
| Amazon ECR | Registro junto ao ambiente AWS, com controle por IAM e referências por digest; não exige credencial do Docker Hub para publicar as imagens da equipe |
| OIDC | Troca a identidade do job por credenciais temporárias de uma role AWS, restrita ao repositório e à branch |
| Um pipeline por serviço | Permite builds independentes e deixa claro qual revisão produziu cada imagem |

Jenkins e Docker Hub seriam opções para a entrega, mas a equipe padronizou Actions e ECR. O caminho Jenkins de order e exchange foi retirado; manter dois caminhos atualizando o mesmo workload dificultaria rastrear e controlar os releases. Imagens públicas de base ou ferramentas podem continuar vindo de registros públicos, sem que isso mude o registro de publicação da aplicação.

## Permissões e configuração

A role precisa de permissões de publicação no ECR e de acesso ao cluster, além de RBAC no namespace `store`. A trust policy OIDC deve restringir repositório e branch. O job de release declara `id-token: write`; isso permite solicitar o token OIDC, mas as ações AWS continuam limitadas pela role assumida.

As variáveis incluem região `us-east-2`, cluster `eks-store`, namespace `store`, role e repositório ECR. Order e exchange têm configuração adicional de release e versão do kubectl. Os próprios workflows verificam os valores obrigatórios. Endereços da aplicação ficam em ConfigMaps e senhas em Secrets preparados separadamente.

O deploy usa `registry/repository@sha256:...` e aguarda o rollout. Em falha, consulte os logs do job e o estado do Deployment. Uma reversão para revisão anterior usa `kubectl rollout undo` no contexto e namespace corretos; ela não desfaz migrations de banco.

## Documentação e agregador

O [workflow de documentação](https://github.com/projeto-microservicos/produto/blob/main/.github/workflows/docs.yml) executa `python -m mkdocs build --strict` em PRs. Na `main`, com `PAGES_ENABLED=true`, publica o site no GitHub Pages pelo ambiente `github-pages`.

O workflow `integration.yml` do agregador é uma validação local de integração por Compose, separada do deploy EKS. Seus scripts Python e os templates de preparação não substituem os workflows dos seis serviços. Alterar esta documentação não precisa reconstruir nem implantar as aplicações.

Guias operacionais: [AWS e EKS](deployment.md), [desenvolvimento local](development.md) e [repositório de order](https://github.com/projeto-microservicos/order-service/blob/main/docs/GITHUB-ACTIONS-EKS.md).
