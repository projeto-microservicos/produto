# Projeto de microsserviços

Repositório agregador da equipe: fixa versões dos serviços por submodules e publica a documentação com MkDocs no GitHub Pages. O catálogo contempla seis serviços; todos têm repositórios confirmados. Cada serviço mantém seu próprio build, Dockerfile, manifesto Kubernetes e CI/CD com ECR + OIDC.

## Executar o projeto completo

Requisitos: Docker Desktop com containers Linux e Python 3.12+. Na raiz:

```bash
python scripts/project.py init
python scripts/project.py doctor
python scripts/project.py up --monitoring
python scripts/project.py smoke
python scripts/project.py load --profile smoke
python scripts/project.py load --profile ramp
```

Gateway: <http://127.0.0.1:8080>. Prometheus: <http://127.0.0.1:9090>. Grafana: <http://127.0.0.1:3000>, usuário `admin` e senha gerada em `.env`. O dashboard **Store — tráfego, erros e latência** é provisionado automaticamente. Apenas o gateway e as interfaces locais de observabilidade publicam portas no host; os bancos ficam na rede Docker.

O Compose da raiz evita a colisão de porta entre account e exchange dos Composes individuais. Os fluxos de conta, JWT, produtos e autenticação do gateway estão implementados nesta revisão local. As alterações em `services/` pertencem aos respectivos submodules e precisam ser publicadas nesses repositórios antes de atualizar os gitlinks do agregador.

Para parar preservando os bancos: `python scripts/project.py down`. Instruções completas: [desenvolvimento](docs/development.md), [carga e HPA](docs/load-testing.md), [PaaS e custos](docs/costs.md) e [preparação AWS](docs/deployment.md).

Os [resultados da validação](docs/validation.md) registram testes, carga medida e as pendências da entrega.

Decisão de 16/11/2026: manter AWS preparada, sem criar recursos ou ampliar nós; acesso futuro via port-forward. O EKS existente não foi alterado por essa preparação.

## Preparação inicial

Este é o repositório principal [projeto-microservicos/produto](https://github.com/projeto-microservicos/produto). O catálogo `repositories.json` registra as URLs confirmadas de account, auth, gateway, product, exchange e order. O catálogo dos seis serviços está completo.

Em um checkout do repositório principal, execute:

```bash
python scripts/register-submodules.py
git diff --cached
```

O script valida os endereços preenchidos antes de registrar os submodules em `services/` e lista os pendentes. Ele cria `.gitmodules` e gitlinks reais para os commits clonados; não faz commit ou push. Ao receber novas URLs, atualize o catálogo e execute o script novamente. Se esta pasta ainda não tiver seu próprio repositório Git, inicialize primeiro com `git init -b main`.

Depois de revisar e versionar os arquivos do agregador, novos clones usam:

```bash
git clone --recurse-submodules https://github.com/projeto-microservicos/produto.git
```

Se account/auth precisarem também de repositórios de bibliotecas compartilhadas, registre-os conforme o build real desses serviços. Este catálogo inicial representa os seis serviços informados pela equipe.

Os gitlinks fixam commits publicados nos repositórios dos serviços. A referência de order inclui a migração publicada para GitHub Actions, e exchange inclui a API Python, os gargalos opcionais e as pipelines Jenkins/GitHub Actions. A preparação do agregador não faz deploy dos serviços.

## Documentação local

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# PowerShell: .venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python -m mkdocs serve
```

Validação: `python -m mkdocs build --strict`. A documentação não depende de clonar os submodules para compilar.

## GitHub Pages

Em **Settings → Pages → Build and deployment**, selecione **GitHub Actions**. Configure a variável Actions `PAGES_ENABLED=true`. O workflow `docs.yml` valida PRs e publica a documentação nos pushes de `main`, ou por execução manual em `main`. O endereço publicado aparece no job de deploy. Ele usa o domínio padrão `github.io`, sem contratação de domínio ou recurso AWS.

Consulte [custos e responsabilidades](docs/costs.md) antes de ativar recursos pagos. O pipeline da documentação publica o site estático; a implantação dos serviços segue o roteiro separado de AWS.
