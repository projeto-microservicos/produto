# Projeto de microsserviços

Repositório agregador da equipe: fixa versões dos serviços por submodules e publica a documentação com MkDocs no GitHub Pages. O catálogo contempla seis serviços; todos têm repositórios confirmados. Cada serviço mantém seu próprio build, Dockerfile, manifesto Kubernetes e CI/CD com ECR + OIDC.

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

Consulte [custos e responsabilidades](docs/costs.md) antes de ativar recursos pagos. O código preparado não cria infraestrutura, publica serviços ou configura faturamento.
