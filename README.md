# Projeto de microsserviços

Agregador da loja da equipe: fixa versões dos seis serviços e do front end por submodules e publica a documentação com MkDocs no GitHub Pages. Cada serviço mantém seu próprio build, Dockerfile, manifests e GitHub Actions.

## Entrega (Plataformas 2026.2)

| Material | Link |
|---|---|
| **Vídeo da apresentação** (1 min 57 s, legendado) | <https://youtu.be/MZCj2nR3Db8> |
| **Documentação** (MkDocs no GitHub Pages) | <https://projeto-microservicos.github.io/produto/> |
| Documentação em PDF | [docs/assets/documentacao.pdf](docs/assets/documentacao.pdf) |
| Loja no ar (front end, servido pelo gateway no EKS) | <http://a488cbb85e8304108b4f9563359cf260-811be60b7d8b4e24.elb.us-east-2.amazonaws.com/app/> |
| Slides | [PowerPoint](docs/assets/apresentacao.pptx) e [PDF](docs/assets/apresentacao.pdf) |
| Equipe | João Ricardo ([joaorcmr](https://github.com/joaorcmr)) e [adventurescumm](https://github.com/adventurescumm); ver [equipe e autoria](docs/team.md) |

Repositórios, todos em `services/` como submodules: [gateway-service](https://github.com/projeto-microservicos/gateway-service), [auth-service](https://github.com/projeto-microservicos/auth-service), [account-service](https://github.com/projeto-microservicos/account-service), [product-service](https://github.com/projeto-microservicos/product-service), [order-service](https://github.com/projeto-microservicos/order-service), [exchange-service](https://github.com/projeto-microservicos/exchange-service) e [frontend-service](https://github.com/projeto-microservicos/frontend-service).

## Arquitetura e operação

O ambiente de referência de 20/11/2026 é o EKS `eks-store`, em `us-east-2`, com três nós `t2.small`, RDS PostgreSQL privado e RabbitMQ no namespace `store`. O NLB expõe o gateway, que também serve o front end em `/app/`; os demais serviços ficam internos. Desde 20/11 os nós ficam ligados o tempo todo. Antes, desligavam de 23:59 a 06:00, o que economizava só ~5% da conta (ver [custos](docs/costs.md)).

- [Arquitetura e contratos](docs/architecture.md)
- [Seis serviços e health-checks](docs/index.md) e o [front end](docs/services/frontend.md)
- [AWS e EKS](docs/deployment.md)
- [CI/CD com GitHub Actions, ECR e OIDC](docs/ci-cd.md)
- [Mensageria e EDA](docs/mensageria.md)
- [Teste de carga e HPA](docs/load-testing.md)
- [Custos, PaaS e SLA](docs/costs.md)
- [Equipe e autoria](docs/team.md)

O caminho de release do EKS é o workflow de cada serviço. Os scripts Python e templates do agregador são ferramentas de laboratório e preparação; não substituem esse fluxo.

## Desenvolvimento local

Requisitos: Docker Desktop com containers Linux e Python 3.12+. Clone os serviços nas versões fixadas:

```bash
git clone --recurse-submodules https://github.com/projeto-microservicos/produto.git
cd produto
git submodule update --init --recursive
python scripts/project.py init
python scripts/project.py up --monitoring
python scripts/project.py smoke
```

O Compose local publica o gateway em `http://127.0.0.1:8080`, Prometheus em `http://127.0.0.1:9090` e Grafana em `http://127.0.0.1:3000`. As senhas ficam no `.env` local. Para parar preservando os dados, use `python scripts/project.py down`. Consulte [desenvolvimento local](docs/development.md) para testes, carga e atualização de gitlinks.

Os resultados em [validação](docs/validation.md) são registros datados; as medições locais não estimam a capacidade do EKS.

## Documentação local e publicação

```bash
python -m venv .venv
# PowerShell: .venv/Scripts/Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m mkdocs build --strict
python -m mkdocs serve
```

O workflow `docs.yml` valida as PRs. Após revisão e merge na `main`, publica o Pages quando `PAGES_ENABLED=true` e o ambiente `github-pages` permite o deploy. A documentação compila sem clonar os submodules. O catálogo `repositories.json` e o script `scripts/register-submodules.py` mantêm o registro inicial dos repositórios.

## Apresentação

O [vídeo final](https://youtu.be/MZCj2nR3Db8) tem 1 min 57 s, com legenda em português, e está também embutido na [página de apresentação](docs/presentation.md), junto com o roteiro e a forma como cada trecho foi gravado no EKS. Os [slides editáveis](docs/assets/apresentacao.pptx) e a [versão PDF](docs/assets/apresentacao.pdf) foram usados no vídeo. Para regenerar os slides, instale `presentation/requirements.txt` e execute `python presentation/build.py`.

A distribuição de responsabilidades e a assistência de IA estão descritas em [equipe e autoria](docs/team.md) e nos READMEs dos serviços.
