# Desenvolvimento

## Ambiente integrado

Use Docker Desktop com containers Linux e Python 3.12+. O build usa JDK 25 e Maven dentro do Docker; não depende do Java padrão do Windows.

```bash
python scripts/project.py init
python scripts/project.py doctor
python scripts/project.py up --monitoring
python scripts/project.py smoke
```

A inicialização gera senhas e uma chave JWT em `.env`, sem sobrescrever um arquivo existente. Guarde esse arquivo: trocar uma senha no `.env` não altera a senha de um PostgreSQL que já tem volume inicializado. O `down` preserva os volumes. Não use `down -v` se quiser manter os dados.

O teste de ponta a ponta usa `http://127.0.0.1:8080`, registra duas contas sintéticas, autentica, verifica token inválido e falsificação de `id-account`, cria um produto e um pedido de USD 20,24, verifica isolamento entre contas e remove o produto de teste. As contas e o pedido permanecem no banco. Para também validar uma conversão BRL com o provedor real:

```bash
python scripts/smoke.py --live-exchange
```

Redis, RabbitMQ, JWT próprio de order e pagamentos ficam desligados no ambiente integrado, como no Deployment atual. O gateway autentica as chamadas. O USD/USD do exchange permite carga sem enviar tráfego ao provedor externo.

## Testes automatizados

```bash
python -m venv .venv
# PowerShell
.venv/Scripts/python.exe -m pip install -r requirements.txt -r services/exchange/requirements-dev.txt
.venv/Scripts/python.exe scripts/project.py test
```

`test` executa os cinco projetos Java em containers Maven e os testes Python/Bash em Linux. As dependências Python são instaladas no container de testes. Esse caminho também funciona no Windows e preserva os testes Bash dos pipelines. Os testes de integração opcionais de Redis/RabbitMQ continuam condicionados aos scripts próprios desses serviços.

Para observar a execução: `python scripts/project.py status`, `python scripts/project.py logs`, Prometheus em <http://127.0.0.1:9090> e Grafana em <http://127.0.0.1:3000>. A senha do usuário Grafana `admin` está em `GRAFANA_PASSWORD` no `.env`.

## Clonar e atualizar o agregador

```bash
git clone --recurse-submodules https://github.com/projeto-microservicos/produto.git
cd produto
git submodule update --init --recursive
git submodule status --recursive
```

Cada submodule fixa um commit. Para atualizar um serviço, escolha o commit revisado no repositório dele, depois versione o novo gitlink no agregador:

```bash
git -C services/order fetch origin
git -C services/order checkout COMMIT_REVISADO
git add services/order
git diff --cached --submodule
```

O commit no agregador não publica o serviço. Cada repositório executa seus próprios testes e seu próprio pipeline de release. Faça alterações de código em uma branch no submodule e publique-as no repositório daquele serviço antes de atualizar a referência do agregador.

## Executar order localmente

Requisitos: JDK 25, Maven 3.9+ e Docker Compose. Na pasta `services/order`:

```bash
mvn -B -ntp verify
python scripts/init-env.py
docker network create store-dev
docker compose up --build -d --wait --wait-timeout 300
```

Crie a rede apenas uma vez. Product e exchange precisam estar na mesma rede como `product:8080` e `exchange:8080`, ou ter suas URLs configuradas. O Compose de order mantém seu PostgreSQL local; Redis/RabbitMQ locais permitem validar os gargalos sem habilitá-los no EKS.

## Validar documentação

```bash
python -m pip install -r requirements.txt
python -m mkdocs build --strict
python -m mkdocs serve
```

Os PRs do agregador validam a documentação. Os testes de cada serviço continuam no CI/CD do respectivo repositório.

O workflow `integration.yml` é uma verificação de integração local: constrói os seis serviços fixados nos submodules, verifica o fluxo pelo gateway e roda o perfil curto k6. O runner precisa conseguir clonar cada repositório, inclusive o produto privado, e inicializar a configuração local antes do Compose. Ele não faz deploy AWS; o caminho de produção está em [CI/CD](ci-cd.md).
