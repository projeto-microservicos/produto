# Testes de carga e HPA

O [exercício de carga](https://insper.github.io/platform/pt/2026.2/exercises/project/load-testing/) pede um vídeo com o gerador de carga e o HPA em execução. A aplicação usa `/products`, `/orders` e `/exchanges`; não oferece o `/info` usado como exemplo no enunciado.

Os [resultados já medidos](validation.md) registram a validação desta revisão.

## Validar a carga com Compose

```bash
python scripts/project.py up --monitoring
python scripts/project.py smoke
python scripts/project.py load --profile smoke
python scripts/project.py load --profile ramp
```

O teste curto usa um usuário por 15 segundos. A rampa sobe de 1 para 5 usuários em 1 minuto, chega a 30 em mais 2 minutos, sustenta 30 por 3 minutos e reduz a zero em 1 minuto. O `setup` cria uma conta, um produto e um pedido. Durante a carga são feitas três leituras autenticadas por iteração; o produto é excluído no fim. Contas e pedidos sintéticos permanecem no banco. Não há criação contínua de pedidos nem chamadas ao provedor público de câmbio.

O arquivo `artifacts/k6-summary.json` registra contagem de requisições, vazão, percentis, taxa de falhas e resultado dos thresholds. O comando retorna erro quando as falhas superam 1%, p95 atinge 1 segundo ou as verificações ficam abaixo de 99%. Esses limites são metas iniciais do projeto. Guarde o JSON de cada execução com nome próprio antes de repetir.

O dashboard Grafana **Store — tráfego, erros e latência** mostra vazão, 5xx, p95 e CPU por serviço. Compose não tem HPA: essa execução comprova apenas o comportamento sob carga.

## Demonstrar HPA sem gastos AWS

Requisitos adicionais: Minikube e kubectl instalados; ambiente virtual com PyYAML. Reserve aproximadamente 4 GiB para o cluster. Em máquinas com Docker limitado a 8 GiB, conclua a carga Compose e pare esse ambiente antes de iniciar o cluster local:

```bash
python scripts/project.py down
.venv/Scripts/python.exe scripts/local-k8s.py start
```

O script cria o perfil `store-local`, mantém o contexto atual do kubectl e usa explicitamente o contexto local em todas as operações. Carrega as seis imagens já construídas, habilita Metrics Server, inicia PostgreSQL com volume local e aplica o HPA do gateway. Credenciais e manifesto gerados ficam em `.local/`, ignorado pelo Git. Esse PostgreSQL é somente para demonstração e não comprova uso de RDS.

Abra três terminais para gravar:

```bash
# Terminal 1: iniciar a carga dentro do cluster
.venv/Scripts/python.exe scripts/local-k8s.py load
kubectl --context store-local -n store-demo logs -f job/store-load
```

```bash
# Terminal 2: observar réplicas e uso de CPU usado pelo HPA
kubectl --context store-local -n store-demo get hpa -w
```

```bash
# Terminal 3: observar pods que entram e saem
kubectl --context store-local -n store-demo get pods -w
```

O HPA usa CPU alvo de 50% do request do gateway, varia de 1 a 3 réplicas e aguarda 120 segundos antes de reduzir. Mostre o estado inicial, a subida da carga, novas réplicas prontas e a redução após o fim. `kubectl --context store-local -n store-demo top pods` ajuda a diagnosticar. O HPA altera pods; ele não adiciona nós. Uma réplica `Pending` não comprova capacidade disponível.

Aguarde a primeira leitura válida de CPU antes de gravar; `<unknown>` durante o início do Metrics Server é temporário. Para salvar a sequência automaticamente em paralelo à carga, use `python scripts/observe-hpa.py`. O arquivo JSONL contém horário UTC, réplicas atuais/desejadas/prontas, CPU e situação do Job. O observador termina quando o Job acaba e o gateway volta a uma réplica pronta, ou após 11 minutos.

A carga roda em um Job de no máximo 10 minutos e usa `http://gateway:8080` pelo Service, distribuindo requisições entre as réplicas. Port-forward aponta para um pod e deve ser reservado ao teste funcional. O resumo JSON também aparece no log do Job como `SUMMARY_JSON=...`; não contém tokens. Para repetir, remova apenas o Job terminado:

```bash
kubectl --context store-local -n store-demo delete job store-load
.venv/Scripts/python.exe scripts/local-k8s.py load
```

Para acesso funcional local ao cluster: `kubectl --context store-local -n store-demo port-forward svc/gateway 18080:8080` e, em outro terminal, `python scripts/smoke.py --base-url http://127.0.0.1:18080`.

Ao terminar: `.venv/Scripts/python.exe scripts/local-k8s.py stop`. Isso para o cluster local e preserva o volume. Depois, `python scripts/project.py up --monitoring` restaura o ambiente Compose.

## Repetir no EKS quando a implantação for liberada

O cluster `eks-store` já tem Metrics Server, mas a implantação completa depende de banco e capacidade. O usuário escolheu não criar recursos pagos nesta etapa. Após resolver essas dependências, execute os mesmos manifestos `k8s/hpa.yaml` e `k8s/load-job.yaml` no namespace `store`, criando antes o ConfigMap `store-load-script` a partir de `load/store.js`.

Use sempre `--context arn:aws:eks:us-east-2:533267095490:cluster/eks-store -n store`. Confirme `kubectl top pods`, a existência de requests de CPU e espaço para duas réplicas extras de gateway e o Job. Não aplique o HPA de order, que começa em duas réplicas, no cluster atual sem redimensionamento.

## Evidências da entrega

Guarde o vídeo, data, versão dos serviços, máquina/nós utilizados, perfil de carga, resumo k6, sequência de réplicas do HPA e observações sobre erros/latência. Resultados locais não medem a capacidade do EKS. O vídeo deve mostrar pods prontos atendendo durante a carga, e não apenas a criação do objeto HPA.

Referências: [Kubernetes HPA](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/), [ciclo de vida do k6](https://grafana.com/docs/k6/latest/using-k6/test-lifecycle/), [Minikube start](https://minikube.sigs.k8s.io/docs/commands/start/).
