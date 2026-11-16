# Desenvolvimento

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
