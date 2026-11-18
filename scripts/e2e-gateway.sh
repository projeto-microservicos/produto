#!/usr/bin/env bash
# Teste ponta a ponta da loja, sempre pelo gateway.
#
# Uso:
#   scripts/e2e-gateway.sh http://<DNS do NLB>         # EKS
#   scripts/e2e-gateway.sh http://localhost:8080       # Compose ou kubectl port-forward
#
# O que ele confere:
#   - rotas abertas e internas do gateway;
#   - register, login, refresh e logout;
#   - catálogo;
#   - pedido em USD e convertido (order → exchange → PTAX);
#   - isolamento entre contas, inclusive com o header id-account forjado.
# Cria duas contas descartáveis, um produto e um pedido. No fim, apaga as contas e o produto.
# O pedido fica, porque a API não tem DELETE /orders.
# Faz no máximo duas cotações novas na PTAX (USD e EUR; o exchange guarda cada uma por 5 min).
# Não serve como teste de carga.
#
# Requer curl e jq. Não grava nem imprime senhas ou tokens. Sai com código 1 se algo falhar.
# Escrito com auxílio de IA (Claude) em 18/11/2026.
set -uo pipefail
export LC_ALL=C

BASE=${1:?"uso: $0 <URL do gateway, por exemplo http://localhost:8080>"}
BASE=${BASE%/}
for cmd in curl jq; do
  command -v "$cmd" >/dev/null || { echo "falta o comando $cmd" >&2; exit 2; }
done

W=$(mktemp -d)
trap 'rm -f "$W/out.json" "$W/hdr.txt"; rmdir "$W"' EXIT
OUT=$W/out.json HDR=$W/hdr.txt
STAMP=$(date +%Y%m%d%H%M%S)
rnd() { LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20; }
PASS_A=$(rnd) PASS_B=$(rnd)
EMAIL_A="e2e-a-$STAMP@example.com" EMAIL_B="e2e-b-$STAMP@example.com"
OK=0 FAIL=0

# req <rótulo> <status esperado> <método> <caminho> [token] [corpo JSON] [header extra]
req() {
  local label=$1 want=$2 method=$3 path=$4 tok=${5:-} body=${6:-} extra=${7:-}
  local args=(-s -o "$OUT" -D "$HDR" -w '%{http_code} %{time_total}' -X "$method" --max-time 20)
  [[ -n $tok ]] && args+=(-H "Authorization: Bearer $tok")
  [[ -n $body ]] && args+=(-H 'Content-Type: application/json' -d "$body")
  [[ -n $extra ]] && args+=(-H "$extra")
  local code time
  read -r code time < <(curl "${args[@]}" "$BASE$path")
  local mark=FAIL
  if [[ $code == "$want" ]]; then mark=ok; OK=$((OK + 1)); else FAIL=$((FAIL + 1)); fi
  printf '%-4s %-62s esperado %s, obtido %s (%s ms)\n' "$mark" "$label" "$want" "$code" \
    "$(awk -v t="$time" 'BEGIN { printf "%.0f", t * 1000 }')"
}

# check <rótulo> <expressão jq sobre a última resposta, que deve dar true>
check() {
  if jq -e "$2" "$OUT" >/dev/null 2>&1; then
    OK=$((OK + 1)); printf 'ok   %s\n' "$1"
  else
    FAIL=$((FAIL + 1)); printf 'FAIL %s :: %s\n' "$1" "$(head -c 300 "$OUT")"
  fi
}

# header <rótulo> <regex, sem diferenciar maiúsculas, sobre os headers da última resposta>
header() {
  if grep -qiE "$2" "$HDR"; then
    OK=$((OK + 1)); printf 'ok   %s\n' "$1"
  else
    FAIL=$((FAIL + 1)); printf 'FAIL %s\n' "$1"
  fi
}

echo "== gateway ($BASE)"
req "GET /gateway/health-check (aberto)" 200 GET /gateway/health-check
req "GET /products sem token" 401 GET /products
req "GET /products com token inválido" 401 GET /products "eyJhbGciOiJIUzI1NiJ9.e30.invalido"
req "POST /auth/solve (rota interna)" 404 POST /auth/solve "" '{"token":"x"}'
req "POST /accounts/login (rota interna)" 404 POST /accounts/login "" '{"email":"x@example.com","password":"x"}'

echo "== auth e account"
req "POST /auth/register A" 201 POST /auth/register "" "{\"name\":\"E2E A\",\"email\":\"$EMAIL_A\",\"password\":\"$PASS_A\"}"
ID_A=$(jq -r .id "$OUT")
check "register devolve o id e não devolve a senha" '(.id | length) == 36 and (has("password") | not)'
req "POST /auth/register com e-mail repetido" 409 POST /auth/register "" "{\"name\":\"E2E A\",\"email\":\"$EMAIL_A\",\"password\":\"$PASS_A\"}"
req "POST /auth/register com senha curta" 400 POST /auth/register "" "{\"name\":\"E2E X\",\"email\":\"x-$STAMP@example.com\",\"password\":\"123\"}"
req "POST /auth/login com senha errada" 401 POST /auth/login "" "{\"email\":\"$EMAIL_A\",\"password\":\"errada-$STAMP\"}"
req "POST /auth/login com o e-mail em maiúsculas" 200 POST /auth/login "" "{\"email\":\"$(tr '[:lower:]' '[:upper:]' <<<"$EMAIL_A")\",\"password\":\"$PASS_A\"}"
req "POST /auth/login A" 200 POST /auth/login "" "{\"email\":\"$EMAIL_A\",\"password\":\"$PASS_A\"}"
TOK_A=$(jq -r .token "$OUT") REF_A=$(jq -r .refreshToken "$OUT")
check "login: Bearer, expiresIn 900 e refresh separado" '.tokenType == "Bearer" and .expiresIn == 900 and (.refreshToken | length) > 20 and .token != .refreshToken'
header "login: cookie __store_jwt_token" '^set-cookie: __store_jwt_token='
header "login: cookie __store_refresh_token com Path=/auth/refresh" '^set-cookie: __store_refresh_token=.*path=/auth/refresh'
req "GET /auth/me" 200 GET /auth/me "$TOK_A"
check "me é a conta A" ".id == \"$ID_A\""
req "GET /accounts (só a própria)" 200 GET /accounts "$TOK_A"
check "lista com uma conta, a A" "length == 1 and .[0].id == \"$ID_A\""
req "GET /accounts/{A}" 200 GET "/accounts/$ID_A" "$TOK_A"

echo "== product"
req "POST /products com preço 0" 400 POST /products "$TOK_A" '{"name":"Tomate (teste E2E)","price":0,"unit":"kg"}'
req "POST /products" 201 POST /products "$TOK_A" "{\"name\":\"Tomate (teste E2E $STAMP)\",\"price\":10.12,\"unit\":\"kg\"}"
ID_P=$(jq -r .id "$OUT")
check "produto com preço 10.12 e unidade kg" '.price == 10.12 and .unit == "kg"'
req "GET /products" 200 GET /products "$TOK_A"
check "catálogo contém o produto" "any(.[]; .id == \"$ID_P\")"
req "GET /products?name=<parte do nome>" 200 GET "/products?name=teste%20e2e%20$STAMP" "$TOK_A"
check "busca por nome acha só ele" "length == 1 and .[0].id == \"$ID_P\""
req "GET /products/{id}" 200 GET "/products/$ID_P" "$TOK_A"
req "GET /products/{id inexistente}" 404 GET /products/00000000-0000-0000-0000-000000000000 "$TOK_A"

echo "== order e exchange"
req "POST /orders com produto inexistente" 400 POST /orders "$TOK_A" '{"items":[{"idProduct":"00000000-0000-0000-0000-000000000000","quantity":1}]}'
req "POST /orders (2 × produto)" 201 POST /orders "$TOK_A" "{\"items\":[{\"idProduct\":\"$ID_P\",\"quantity\":2}]}"
ID_O=$(jq -r .id "$OUT")
check "pedido em USD com total 20.24" '.currency == "USD" and .total == 20.24 and (.items | length) == 1'
req "GET /orders" 200 GET /orders "$TOK_A"
check "lista contém o pedido" "any(.[]; .id == \"$ID_O\")"
req "GET /orders/{id} (USD)" 200 GET "/orders/$ID_O" "$TOK_A"
check "pedido em USD" '.currency == "USD" and .total == 20.24'
req "GET /orders/{id}?currency=BRL (order → exchange → PTAX)" 200 GET "/orders/$ID_O?currency=BRL" "$TOK_A"
check "pedido convertido para BRL" '.currency == "BRL" and .total > 20.24'
echo "     total em BRL: $(jq -r .total "$OUT")"
req "GET /orders/{id}?currency=XYZ" 422 GET "/orders/$ID_O?currency=XYZ" "$TOK_A"
req "GET /exchange/USD/BRL" 200 GET /exchange/USD/BRL "$TOK_A"
check "cotação com sell, buy, date e o id-account de A" "(.sell > 0) and (.buy > 0) and (.date | test(\"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$\")) and .[\"id-account\"] == \"$ID_A\""
echo "     USD→BRL: $(jq -c '{sell, buy, date}' "$OUT")"
req "GET /exchanges/USD/EUR (plural; taxa cruzada pelo BRL)" 200 GET /exchanges/USD/EUR "$TOK_A"
echo "     USD→EUR: $(jq -c '{sell, buy, date}' "$OUT")"
req "GET /exchange/USD/BRL de novo" 200 GET /exchange/USD/BRL "$TOK_A"
header "a segunda cotação vem do cache (X-Cache: hit)" '^x-cache: hit'
req "GET /exchange/USD/XYZ" 422 GET /exchange/USD/XYZ "$TOK_A"

echo "== isolamento entre contas"
req "POST /auth/register B" 201 POST /auth/register "" "{\"name\":\"E2E B\",\"email\":\"$EMAIL_B\",\"password\":\"$PASS_B\"}"
ID_B=$(jq -r .id "$OUT")
req "POST /auth/login B" 200 POST /auth/login "" "{\"email\":\"$EMAIL_B\",\"password\":\"$PASS_B\"}"
TOK_B=$(jq -r .token "$OUT") REF_B=$(jq -r .refreshToken "$OUT")
req "GET /orders/{pedido de A} com B" 404 GET "/orders/$ID_O" "$TOK_B"
req "GET /orders com B" 200 GET /orders "$TOK_B"
check "B não vê os pedidos de A" 'length == 0'
req "GET /accounts/{A} com B" 404 GET "/accounts/$ID_A" "$TOK_B"
req "DELETE /accounts/{A} com B" 404 DELETE "/accounts/$ID_A" "$TOK_B"
req "GET /orders/{pedido de A} com B e id-account de A forjado" 404 GET "/orders/$ID_O" "$TOK_B" "" "id-account: $ID_A"
req "GET /auth/me A depois das tentativas de B" 200 GET /auth/me "$TOK_A"

echo "== refresh, logout e conta apagada"
req "POST /auth/refresh com o access token no lugar do refresh" 401 POST /auth/refresh "" "{\"refreshToken\":\"$TOK_A\"}"
req "POST /auth/refresh A" 200 POST /auth/refresh "" "{\"refreshToken\":\"$REF_A\"}"
check "refresh devolve um par novo" "(.token | length) > 20 and .token != \"$TOK_A\""
TOK_A2=$(jq -r .token "$OUT")
req "GET /auth/me com o access token renovado" 200 GET /auth/me "$TOK_A2"
req "GET /orders com o refresh token como Bearer" 401 GET /orders "$REF_A"
req "POST /auth/logout" 204 POST /auth/logout
header "logout expira o cookie do access token" '^set-cookie: __store_jwt_token=;.*max-age=0'
req "DELETE /accounts/{B} com B" 204 DELETE "/accounts/$ID_B" "$TOK_B"
req "POST /auth/login com a conta B apagada" 401 POST /auth/login "" "{\"email\":\"$EMAIL_B\",\"password\":\"$PASS_B\"}"
req "POST /auth/refresh com a conta B apagada" 401 POST /auth/refresh "" "{\"refreshToken\":\"$REF_B\"}"

echo "== limpeza"
req "DELETE /products/{id}" 204 DELETE "/products/$ID_P" "$TOK_A2"
req "DELETE /accounts/{A}" 204 DELETE "/accounts/$ID_A" "$TOK_A2"

echo
echo "RESUMO: $OK ok, $FAIL falhas. O pedido $ID_O fica no banco (não há DELETE /orders)."
[[ $FAIL -eq 0 ]]
