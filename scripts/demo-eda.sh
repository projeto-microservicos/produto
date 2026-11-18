#!/usr/bin/env bash
# Demonstração da mensageria (EDA) no EKS: o gargalo escolhido (BOT-05).
#
# Uso:
#   scripts/demo-eda.sh http://<DNS do NLB>
#   PAUSA=1 scripts/demo-eda.sh http://<DNS do NLB>   # espera Enter entre as etapas (para gravar)
# Requer curl, jq, python3 e kubectl com acesso ao namespace store.
#
# Quatro demonstrações, nesta ordem:
#   1. Linha de base: o POST /orders responde sem esperar a confirmação, que o consumidor faz depois.
#   2. Broker fora do ar: o RabbitMQ vai a 0 réplicas. Os pedidos continuam com 201 e esperam na outbox.
#      Com o broker de volta, a outbox drena e cada pedido é confirmado uma vez só.
#   3. Mensagem envenenada: um payload inválido vai direto para a DLQ orders.created.dlq, sem loop.
#   4. Consumidor lento (ORDER_WORKER_DELAY=3s): a latência do POST não muda. As confirmações saem a
#      cada 3 s, e a fila enche e esvazia.
#
# ATENÇÃO: o script MUDA O CLUSTER. Ele escala o StatefulSet rabbitmq e altera o env do Deployment order.
# Com maxSurge 0, cada rollout do order derruba o order por ~1 min.
# No fim, ou com Ctrl+C, ele sempre volta ao normal: rabbitmq com 1 réplica e ORDER_WORKER_DELAY removido.
# Cria uma conta e um produto descartáveis e apaga os dois no fim. Os pedidos ficam, porque não há DELETE /orders.
# Leva de 6 a 8 minutos. Cada comando que altera o cluster aparece na tela antes de rodar.
# Escrito com auxílio de IA (Claude) em 18/11/2026.
set -uo pipefail
export LC_ALL=C

BASE=${1:?"uso: $0 <URL do gateway>"}
BASE=${BASE%/}
NS=${NS:-store}
DELAY=${DELAY:-3s}
for cmd in curl jq kubectl python3; do
  command -v "$cmd" >/dev/null || { echo "falta o comando $cmd" >&2; exit 2; }
done
kubectl -n "$NS" get statefulset/rabbitmq deploy/order >/dev/null || exit 2

W=$(mktemp -d)
OUT=$W/out.json
SCALED=0 CHANGED_DELAY=0 TOK="" ID_P="" ID_A=""
STAMP=$(date +%Y%m%d%H%M%S)
EMAIL="demo-eda-$STAMP@example.com"
PASS=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20)

kube() { echo "  + kubectl -n $NS $*"; kubectl -n "$NS" "$@"; }
etapa() {
  echo; echo "================ $* ================"
  [[ ${PAUSA:-0} == 1 ]] && read -r -p "(Enter para continuar) " _
  return 0
}
api() { # api <método> <caminho> [corpo] → grava a resposta em $OUT e imprime "status tempo"
  local args=(-s -o "$OUT" -w '%{http_code} %{time_total}' -X "$1" --max-time 20)
  [[ -n $TOK ]] && args+=(-H "Authorization: Bearer $TOK")
  [[ -n ${3:-} ]] && args+=(-H 'Content-Type: application/json' -d "$3")
  curl "${args[@]}" "$BASE$2"
}
login() {
  read -r _ _ < <(api POST /auth/login "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
  TOK=$(jq -r .token "$OUT")
}
metric() { # metric <nome> <result> → valor do contador no order (0 se ainda não existe)
  kubectl get --raw "/api/v1/namespaces/$NS/services/order-metrics:management/proxy/actuator/prometheus" 2>/dev/null \
    | awk -v n="$1{" -v r="result=\"$2\"" 'index($1, n) == 1 && index($1, r) { v = int($2) } END { print v + 0 }'
}
filas() { kubectl -n "$NS" exec rabbitmq-0 -- rabbitmqctl list_queues -q name messages consumers 2>/dev/null | column -t; }
order_pod() { kubectl -n "$NS" get pods -l app=order --sort-by=.metadata.creationTimestamp -o name | tail -1; }

pedidos() { # pedidos <n> <arquivo> → cria n pedidos em sequência e anota id, data, status e tempo
  : >"$2"
  for _ in $(seq 1 "$1"); do
    local code t
    read -r code t < <(api POST /orders "{\"items\":[{\"idProduct\":\"$ID_P\",\"quantity\":1}]}")
    printf '%s\t%s\t%s\t%s\n' "$(jq -r '.id // "-"' "$OUT")" "$(jq -r '.date // "-"' "$OUT")" "$code" "$t" >>"$2"
    printf '  POST /orders → %s em %4.0f ms\n' "$code" "$(awk -v t="$t" 'BEGIN { print t * 1000 }')"
  done
}
confirmacoes() { # confirmacoes <arquivo de pedidos> → quanto tempo depois do pedido saiu cada confirmação
  kubectl -n "$NS" logs "$(order_pod)" --since=15m 2>/dev/null | grep 'confirmed: confirmation sent' >"$W/conf.log"
  python3 - "$1" "$W/conf.log" <<'PY'
import datetime as dt, re, sys
conf = {}
for line in open(sys.argv[2]):
    m = re.match(r'(\S+?)Z .*Order (\S+) confirmed', line)
    if m:
        conf.setdefault(m.group(2), []).append(dt.datetime.fromisoformat(m.group(1)).replace(tzinfo=dt.timezone.utc))
lat, lag = [], []
for oid, date, code, t in (l.rstrip('\n').split('\t') for l in open(sys.argv[1])):
    lat.append(float(t) * 1000)
    seen = conf.get(oid, [])
    if oid == '-' or not seen:
        print(f'  pedido {oid[:8]}: sem confirmação'); continue
    d = dt.datetime.fromisoformat(date.replace('Z', '+00:00'))
    g = (seen[0] - d).total_seconds()
    lag.append(g)
    print(f'  pedido {oid[:8]}: POST {float(t) * 1000:4.0f} ms · confirmado {g:5.1f} s depois · {len(seen)}x')
lat.sort(); lag.sort()
print(f'  → POST mediana {lat[len(lat) // 2]:.0f} ms · {len(lag)}/{len(lat)} confirmados'
      + (f' · atraso mediano {lag[len(lag) // 2]:.1f} s, máximo {lag[-1]:.1f} s' if lag else ''))
PY
}
espera_confirmar() { # espera_confirmar <processed inicial> <quantos> <timeout s>
  local fim=$((SECONDS + $3)) n
  while ((SECONDS < fim)); do
    n=$(($(metric orders_events_consumed_total processed) - $1))
    echo "  confirmados até agora: $n de $2"
    ((n >= $2)) && return 0
    sleep 5
  done
  return 1
}

restaura() {
  local rc=$?
  trap - EXIT INT TERM
  echo; echo "================ voltando ao normal ================"
  if [[ $SCALED == 1 ]]; then
    kube scale statefulset/rabbitmq --replicas=1
    kubectl -n "$NS" rollout status statefulset/rabbitmq --timeout=180s
  fi
  if [[ $CHANGED_DELAY == 1 ]]; then
    kube set env deploy/order ORDER_WORKER_DELAY-
    kubectl -n "$NS" rollout status deploy/order --timeout=300s
  fi
  if [[ -n $ID_A ]]; then
    login
    [[ -n $ID_P ]] && echo "  DELETE /products/$ID_P → $(api DELETE "/products/$ID_P" | cut -d' ' -f1)"
    echo "  DELETE /accounts/$ID_A → $(api DELETE "/accounts/$ID_A" | cut -d' ' -f1)"
  fi
  rm -f "$W"/*.json "$W"/*.tsv "$W"/*.log; rmdir "$W"
  exit "$rc"
}
trap restaura EXIT
trap 'exit 130' INT TERM

etapa "preparação: conta e produto descartáveis"
read -r code _ < <(api POST /auth/register "{\"name\":\"Demo EDA\",\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
[[ $code == 201 ]] || { echo "register falhou ($code): $(head -c 300 "$OUT")"; exit 1; }
ID_A=$(jq -r .id "$OUT")
login
read -r code _ < <(api POST /products "{\"name\":\"Demo EDA $STAMP\",\"price\":1.00,\"unit\":\"un\"}")
[[ $code == 201 ]] || { echo "POST /products falhou ($code)"; exit 1; }
ID_P=$(jq -r .id "$OUT")
echo "  conta $ID_A · produto $ID_P"
filas

etapa "1/4 linha de base: o POST /orders não espera o consumidor"
pedidos 5 "$W/base.tsv"
sleep 3
confirmacoes "$W/base.tsv"

etapa "2/4 broker fora do ar: os pedidos continuam e esperam na outbox"
P0=$(metric orders_events_consumed_total processed) R0=$(metric orders_outbox_deliveries_total retry)
kube scale statefulset/rabbitmq --replicas=0
SCALED=1
kubectl -n "$NS" wait --for=delete pod/rabbitmq-0 --timeout=120s >/dev/null 2>&1
echo "  RabbitMQ fora do ar: $(kubectl -n "$NS" get pods -l app=rabbitmq --no-headers 2>/dev/null | wc -l | tr -d ' ') pod(s)"
pedidos 5 "$W/queda.tsv"
sleep 10
echo "  outbox: $(($(metric orders_outbox_deliveries_total retry) - R0)) tentativas de entrega falharam e vão ser repetidas"
echo "  confirmados com o broker fora: $(($(metric orders_events_consumed_total processed) - P0)) (esperado 0)"
kube scale statefulset/rabbitmq --replicas=1
kubectl -n "$NS" rollout status statefulset/rabbitmq --timeout=180s
SCALED=0
echo "  broker de volta; a outbox reenvia com backoff (2, 4, 8, 16, 32 s…)"
espera_confirmar "$P0" 5 180 || echo "  ainda faltam confirmações (veja os logs do order)"
confirmacoes "$W/queda.tsv"
echo "  eventos repetidos ignorados pela idempotência: $(metric orders_events_consumed_total duplicate)"
filas

etapa "3/4 mensagem envenenada: vai para a DLQ, sem loop"
J0=$(metric orders_events_consumed_total rejected)
echo "  + kubectl -n $NS exec rabbitmq-0 -- (publica 'isto nao e um OrderCreated' em store.orders/created)"
kubectl -n "$NS" exec rabbitmq-0 -- sh -c 'AUTH=$(printf "%s:%s" "$RABBITMQ_DEFAULT_USER" "$RABBITMQ_DEFAULT_PASS" | base64 | tr -d "\n");
  wget -qO- --header "Authorization: Basic $AUTH" --header "Content-Type: application/json" \
    --post-data "{\"properties\":{\"message_id\":\"poison-demo\"},\"routing_key\":\"created\",\"payload\":\"isto nao e um OrderCreated\",\"payload_encoding\":\"string\"}" \
    "http://127.0.0.1:15672/api/exchanges/%2F/store.orders/publish"'
echo
sleep 3
echo "  rejeitados pelo consumidor: $(($(metric orders_events_consumed_total rejected) - J0)) (esperado 1)"
filas

etapa "4/4 consumidor lento (ORDER_WORKER_DELAY=$DELAY): o POST não fica mais lento"
kube set env deploy/order "ORDER_WORKER_DELAY=$DELAY"
CHANGED_DELAY=1
kubectl -n "$NS" rollout status deploy/order --timeout=300s
P1=$(metric orders_events_consumed_total processed)
pedidos 5 "$W/lento.tsv"
for _ in 1 2 3; do
  echo "  fila: $(kubectl -n "$NS" exec rabbitmq-0 -- rabbitmqctl list_queues -q name messages_ready messages_unacknowledged 2>/dev/null | awk '$1 == "orders.created" { print "orders.created prontas=" $2 ", em processamento=" $3 }')"
  sleep 3
done
espera_confirmar "$P1" 5 90 || echo "  ainda faltam confirmações (veja os logs do order)"
confirmacoes "$W/lento.tsv"

echo
echo "Concluído. A etapa 'voltando ao normal' remove o ORDER_WORKER_DELAY (mais um rollout do order) e apaga a conta e o produto."
