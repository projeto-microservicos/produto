# Teste de carga e HPA

O enunciado pede um teste de carga na aplicação Spring Boot e um vídeo que mostre **a carga rodando** e **o HPA escalando**. Usamos o [k6](https://grafana.com/docs/k6/latest/) contra o gateway, que é Spring Cloud Gateway, e um HPA no Deployment do gateway, no EKS.

## O que roda

| Peça | Arquivo | Resumo |
|---|---|---|
| Script de carga | `load/store.js` | k6 1.6.1 (imagem `grafana/k6`, fixada por digest) |
| Alvo principal | `TARGET=gateway` | `GET /gateway/health-check`, que o próprio gateway responde sem token e sem chamar outro serviço. Equivale ao `/info` do enunciado, que o nosso gateway só expõe na porta interna. Isola a CPU do gateway, que é o que o HPA mede |
| Cenário completo (opcional) | `TARGET=store` | Cria conta, produto e pedido. Depois faz leituras autenticadas de produto, pedido e câmbio USD→USD, cada uma passando por gateway → auth → serviço. Moeda igual não chama a PTAX |
| Autoscaler | `k8s/hpa.yaml` | gateway com alvo de 50% do request de CPU (100m), de 1 a 3 réplicas, sobe 1 pod a cada 30 s e espera 120 s antes de reduzir |
| Alternativa dentro do cluster | `k8s/load-job.yaml` | o mesmo script num Job, pelo Service do gateway (não calibrado no EKS) |

**Por que no máximo 3 réplicas.** Os nós são t2.small, com 940m de CPU, ~1,45 GiB e 11 pods alocáveis cada. Em 18/11, só um dos 3 nós tinha folga para mais duas réplicas do gateway (100m e 320 MiB reservados cada). Com `--max=10`, como no exemplo do enunciado, sete réplicas ficariam `Pending`. O HPA cria pods; ele não cria nós.

## Calibração (18/11/2026)

Carga de uma máquina fora da AWS, pelo NLB, contra o `/gateway/health-check`, com 1 réplica do gateway e sem HPA:

| Carga | Vazão | p95 | Falhas | CPU do gateway | Réplicas que o HPA pediria |
|---|---|---|---|---|---|
| 60 VUs, sem pausa, 90 s | 416 req/s | 154 ms | 0% | ~55m (55% do request) | 1 ou 2: está no limiar, e o HPA tolera 10% |
| 150 VUs, sem pausa, 60 s | 1.039 req/s | 154 ms | 0% | ~112m (112%) | 3, porque `ceil(1 × 112 / 50) = 3`, limitado ao máximo |

Os dois testes tiveram o mesmo p95, que é basicamente o caminho de rede até us-east-2: o gateway não saturou. Com 3 réplicas, cada pod fica em ~37m (74% do alvo) e a escala se mantém estável.

## Antes de começar

1. Confira se os 3 nós estão `Ready` (`kubectl get nodes`). O desligamento noturno foi removido em 20/11 e o cluster fica ligado o tempo todo.
2. Confira se o metrics-server responde: `kubectl -n store top pods`.
3. Confira se algum nó tem folga para mais **duas** réplicas do gateway: 200m de CPU, 640 MiB de memória reservada e 2 vagas de pod. Os nós são recriados toda manhã, então isso muda de um dia para o outro.

    ```bash
    for n in $(kubectl get nodes -o name); do
      echo "$n · pods: $(kubectl get pods -A --field-selector spec.nodeName=${n#node/} --no-headers | wc -l)/11"
      kubectl describe "$n" | sed -n '/Allocated resources/,/Events/p' | grep -E '^\s+(cpu|memory)'
    done
    ```

    Se nenhum nó tiver essa folga, use `maxReplicas: 2` ou peça um 4º nó temporário. O 4º nó custa ~US$ 0,02 por hora e exige o OK do dono da conta.
4. Não faça merge na `main` do gateway durante a gravação. O deploy reaplica `replicas: 1` e atrapalha o HPA.

## Como gravar (três terminais)

Execute os comandos na raiz do repositório, onde está `load/store.js`, com o contexto do kubectl apontando para o EKS. Para obter o DNS do NLB, consulte o Service público do gateway:

```bash
kubectl -n store get service gateway-public -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

Substitua `<DNS do NLB>` nos comandos abaixo pelo hostname retornado, mantendo o prefixo `http://`.

```bash
# Terminal 1: cria o HPA e acompanha a CPU e as réplicas
kubectl -n store apply -f k8s/hpa.yaml
kubectl -n store get hpa gateway -w
```

```bash
# Terminal 2: acompanha os pods do gateway e os nós onde eles caem
kubectl -n store get pods -l app=gateway -o wide -w
```

```bash
# Terminal 3, Linux/macOS/WSL: a carga (rampa de 7 min, até 150 VUs)
docker run --rm -v "$PWD/load:/load:ro" \
  -e BASE_URL="http://<DNS do NLB>" -e TARGET=gateway -e LOAD_PROFILE=ramp -e MAX_VUS=150 -e SLEEP=0 \
  grafana/k6:1.6.1@sha256:a5ad6bc089a08d77c3ec49f3db8c6fa7a148e4073efcac44c675dbaf3568d8e1 run /load/store.js
```

**No Windows com Git Bash**, use esta versão do terminal 3:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W)/load:/load:ro" \
  -e BASE_URL="http://<DNS do NLB>" -e TARGET=gateway -e LOAD_PROFILE=ramp -e MAX_VUS=150 -e SLEEP=0 \
  grafana/k6:1.6.1@sha256:a5ad6bc089a08d77c3ec49f3db8c6fa7a148e4073efcac44c675dbaf3568d8e1 run /load/store.js
```

O Git Bash converte caminhos como `/load/store.js` para `C:/Program Files/Git/load/store.js`, causando o erro `moduleSpecifier ... couldn't be found`. `MSYS_NO_PATHCONV=1` desativa essa conversão apenas para o comando, e `pwd -W` fornece o caminho Windows da pasta local. As aspas preservam os espaços no nome da pasta. Veja a [orientação do Docker para Git Bash](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/topics/#docker-commands-failing-in-git-bash).

Escreva a URL como `http://`, sem barra invertida antes de `:`. Nos exemplos Bash, o `\` ao fim de uma linha serve apenas para continuar o comando na próxima; a última linha termina em `/load/store.js`, sem `\`.

**No Windows com PowerShell**, use esta versão do terminal 3:

```powershell
docker run --rm -v "${PWD}/load:/load:ro" `
  -e BASE_URL="http://<DNS do NLB>" -e TARGET=gateway -e LOAD_PROFILE=ramp -e MAX_VUS=150 -e SLEEP=0 `
  grafana/k6:1.6.1@sha256:a5ad6bc089a08d77c3ec49f3db8c6fa7a148e4073efcac44c675dbaf3568d8e1 run /load/store.js
```

No PowerShell, `${PWD}` fornece a pasta atual e as aspas preservam os espaços no caminho. O acento grave no fim de cada linha continua o comando e deve ser o último caractere, sem espaços depois. A última linha termina em `/load/store.js`, sem acento grave. Os comandos dos terminais 1 e 2 e a consulta do DNS também funcionam no PowerShell.

Para conferir a montagem e a leitura do script antes da carga, troque `run /load/store.js` por `inspect --include-system-env-vars /load/store.js`. O `inspect` mostra a configuração do teste sem enviar requisições ao gateway; a flag inclui as variáveis de ambiente, como `LOAD_PROFILE` e `MAX_VUS`.

O que deve aparecer:

| Tempo | Carga | HPA |
|---|---|---|
| 0 a 1 min | 1 → 5 VUs | 1 réplica. A coluna `TARGETS` mostra `<unknown>` até a primeira leitura de CPU |
| 1 a 3 min | → 150 VUs | a CPU passa de 50%, e o HPA sobe 1 → 2 → 3, uma réplica a cada 30 s |
| 3 a 6 min | 150 VUs (~1.000 req/s) | 3 réplicas, cada uma com ~37% |
| 6 a 7 min | → 0 | a CPU cai |
| +2 min | — | depois de 120 s estável, volta a 1 réplica |

No fim, apague o HPA, como pede o enunciado: `kubectl -n store delete hpa gateway`.

## Outros cenários

- **Aplicação inteira:** `-e TARGET=store -e MAX_VUS=30 -e SLEEP=0.1`. Cada leitura também chama o `/auth/solve`, então o auth e o nó onde estão as JVMs de auth, product e order passam a dividir a carga. O que aparecer aqui primeiro vale como achado de gargalo.
- **Dentro do cluster:** o `k8s/load-job.yaml` roda o mesmo script pelo Service do gateway, sem a internet no caminho. Como a latência interna é de poucos ms, comece pelo smoke (`LOAD_PROFILE=smoke`) e ajuste `MAX_VUS` e `SLEEP` antes da rampa.

## Cuidados

- **Nunca contra a PTAX:** o `TARGET=gateway` não chama outros serviços, e o `TARGET=store` só pede USD→USD.
- **Créditos de CPU do t2:** sob carga contínua, um t2.small cai para 20% de um vCPU quando os créditos acabam. Testes de até 10 min cabem com folga num nó ligado de manhã.
- **Dados de teste:** o `TARGET=store` apaga a conta e o produto no fim. O pedido fica, porque não há `DELETE /orders`.

## Execução no EKS (20/11/2026)

Rampa completa de 7 min pelo NLB, de uma máquina fora da AWS, contra o `/gateway/health-check`. Gateway `572a8bd`, HPA de `k8s/hpa.yaml` (de 1 a 3 réplicas, alvo de 50% de 100m). Comando do terminal 3 acima, com `SUMMARY_FILE` para guardar o resumo.

**k6:**

| Requisições | Vazão média (rampa inteira) | Mediana | p95 | Máximo | Falhas | Thresholds |
|---:|---:|---:|---:|---:|---:|---|
| 261.706 | 623 req/s | 155 ms | 162 ms | 538 ms | 0,00% | os 3 passaram (`checks > 99%`, falhas < 1%, p95 < 1 s) |

**HPA** (leitura de `kubectl get hpa` e `kubectl top pods` a cada ~13 s; horário de Brasília):

| Hora | Carga | CPU do HPA (média sobre o request) | Réplicas |
|---|---|---|---|
| 09:35:42 | início, 1 → 5 VUs | 8% | 1 |
| 09:36:35 | rampa | 47% | 1 |
| 09:36:55 | rampa | 64%: acima do alvo | **1 → 2** (evento `SuccessfulRescale`) |
| 09:37:26 | rampa | 188% (o pod novo sobe com a JVM ainda aquecendo) | **2 → 3** |
| 09:38:08 a 09:39:15 | 150 VUs | de 66% a 132% enquanto as réplicas novas aquecem | 3 (o máximo) |
| 09:39:29 a 09:42:09 | 150 VUs, depois a descida | de 40% a 49%, cada pod entre 15m e 71m | 3, estável abaixo do alvo |
| 09:42:30 | fim da carga | cai para 2–5% | 3, aguardando os 120 s de estabilização |
| 09:44:56 | — | abaixo do alvo | **3 → 1** (evento "All metrics below target") |

O p95 ficou igual ao da calibração de 18/11 (154 ms contra 162 ms). Ele é dominado pela rede até us-east-2: o gateway não saturou. Os picos de CPU de um pod logo depois de criado (867m e 888m) são o aquecimento da JVM. Por isso o HPA lê médias acima de 100% por cerca de 1 minuto depois de cada escala.

O HPA foi apagado no fim, como pede o enunciado. A gravação do vídeo (trecho B da [apresentação](presentation.md)) repete os mesmos passos e mostra os três terminais.

---

*Autoria: `load/store.js`, `k8s/hpa.yaml` e `k8s/load-job.yaml` vêm da PR #1 de `adventurescumm` (16/11). Em 18/11, o agente do João (Claude) os adaptou ao EKS: incluiu o alvo `gateway` e o perfil `constant`, tirou as credenciais do resumo, fixou a imagem por digest e fez a calibração. Esta página foi escrita com auxílio de IA, como o enunciado permite para a documentação.*
