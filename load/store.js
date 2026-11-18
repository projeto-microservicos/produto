// Teste de carga da loja com k6 (LT-01 e LT-02).
// Adaptado da PR #1 de adventurescumm (16/11/2026). Ajustes para o EKS feitos com auxílio de IA (Claude) em 18/11/2026.
//
// TARGET=gateway (padrão): só GET /gateway/health-check, que o próprio gateway responde, sem token e sem chamar
//   ninguém. Equivale ao "/info" do enunciado e isola a CPU do gateway, que é o que o HPA mede.
// TARGET=store: o setup cria uma conta, um produto e um pedido. Na carga, faz três leituras autenticadas por
//   iteração: produto, pedido e câmbio USD→USD (moeda igual: o exchange responde 1 sem chamar a PTAX).
//   Cada leitura passa por gateway → auth (/auth/solve) → serviço.
// LOAD_PROFILE=smoke: 1 VU por 15 s.
// LOAD_PROFILE=ramp: 1 → 5 VUs em 1 min, → MAX_VUS em 2 min, sustenta 3 min e volta a 0 em 1 min.
// LOAD_PROFILE=constant: MAX_VUS fixos por DURATION (padrão 1m); serve para calibrar.
// SLEEP: pausa entre iterações, em segundos (padrão 0.1).
// SUMMARY_FILE: grava o resumo JSON também nesse caminho (no Job: /results/k6-summary.json).
import http from 'k6/http';
import { check, sleep, fail } from 'k6';

const base = (__ENV.BASE_URL || 'http://gateway:8080').replace(/\/$/, '');
const target = __ENV.TARGET || 'gateway';
const profile = __ENV.LOAD_PROFILE || 'smoke';
const maxVus = Number(__ENV.MAX_VUS || 30);
const pause = Number(__ENV.SLEEP || 0.1);
if (!['gateway', 'store'].includes(target) || !['smoke', 'ramp', 'constant'].includes(profile)
    || !Number.isInteger(maxVus) || maxVus < 1 || maxVus > 500 || !(pause >= 0)) {
  throw new Error('Use TARGET=gateway|store, LOAD_PROFILE=smoke|ramp|constant, MAX_VUS entre 1 e 500 e SLEEP >= 0');
}

const scenarios = {
  smoke: { executor: 'constant-vus', vus: 1, duration: '15s' },
  constant: { executor: 'constant-vus', vus: maxVus, duration: __ENV.DURATION || '1m' },
  ramp: {
    executor: 'ramping-vus', startVUs: 1,
    stages: [{ duration: '1m', target: 5 }, { duration: '2m', target: maxVus },
      { duration: '3m', target: maxVus }, { duration: '1m', target: 0 }],
    gracefulRampDown: '15s',
  },
};

export const options = {
  scenarios: { store: scenarios[profile] },
  thresholds: {
    'http_req_failed{phase:load}': ['rate<0.01'],
    'http_req_duration{phase:load}': ['p(95)<1000'],
    checks: ['rate>0.99'],
  },
};

function json(response, status) {
  if (response.status !== status) fail(`Setup: ${response.request.method} ${response.request.url} esperava ${status}, veio ${response.status}`);
  return response.json();
}

export function setup() {
  if (target === 'gateway') return {};
  const nonce = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const headers = { 'Content-Type': 'application/json' };
  const credentials = { email: `load-${nonce}@example.com`, password: `Load-pass-${nonce}` };
  const account = json(http.post(`${base}/auth/register`, JSON.stringify({ name: 'Load test', ...credentials }), { headers }), 201);
  const token = json(http.post(`${base}/auth/login`, JSON.stringify(credentials), { headers }), 200).token;
  const params = { headers: { ...headers, Authorization: `Bearer ${token}` } };
  const product = json(http.post(`${base}/products`, JSON.stringify({ name: `Load product ${nonce}`, price: 10.12, unit: 'kg' }), params), 201);
  const order = json(http.post(`${base}/orders`, JSON.stringify({ items: [{ idProduct: product.id, quantity: 2 }] }), params), 201);
  return { credentials, accountId: account.id, productId: product.id, orderId: order.id, token };
}

export default function (data) {
  if (target === 'gateway') {
    const res = http.get(`${base}/gateway/health-check`, { tags: { phase: 'load', name: 'GET /gateway/health-check' } });
    check(res, { 'health-check 200': r => r.status === 200 });
    sleep(pause);
    return;
  }
  // O access token dura 15 min, mais do que a rampa (7 min): o mesmo token serve o teste inteiro.
  const params = { headers: { Authorization: `Bearer ${data.token}` }, tags: { phase: 'load', name: 'GET /products/:id' } };
  check(http.get(`${base}/products/${data.productId}`, params), { 'product 200': r => r.status === 200 });
  params.tags.name = 'GET /orders/:id';
  check(http.get(`${base}/orders/${data.orderId}`, params), { 'order 200': r => r.status === 200 });
  params.tags.name = 'GET /exchanges/USD/USD';
  check(http.get(`${base}/exchanges/USD/USD`, params), { 'exchange 200': r => r.status === 200 });
  sleep(pause);
}

export function teardown(data) {
  if (target === 'gateway') return;
  const headers = { 'Content-Type': 'application/json' };
  // Login de novo: o token do setup pode ter expirado se a rampa foi estendida.
  const login = http.post(`${base}/auth/login`, JSON.stringify(data.credentials), { headers });
  if (login.status !== 200) return;
  const auth = { headers: { Authorization: `Bearer ${login.json().token}` } };
  check(http.del(`${base}/products/${data.productId}`, null, auth), { 'limpeza: produto 204': r => r.status === 204 });
  check(http.del(`${base}/accounts/${data.accountId}`, null, auth), { 'limpeza: conta 204': r => r.status === 204 });
}

export function handleSummary(data) {
  const count = data.metrics.http_reqs?.values.count || 0;
  const rate = data.metrics.http_reqs?.values.rate;
  const p95 = data.metrics['http_req_duration{phase:load}']?.values['p(95)'];
  const failures = data.metrics['http_req_failed{phase:load}']?.values.rate;
  const line = `target=${target} profile=${profile} max_vus=${maxVus} requests=${count}`
    + ` rps=${rate === undefined ? '?' : rate.toFixed(1)}`
    + ` p95=${p95 === undefined ? '?' : p95.toFixed(1) + 'ms'}`
    + ` failures=${failures === undefined ? '?' : (failures * 100).toFixed(2) + '%'}\n`;
  const out = { stdout: line };
  // O setup_data traz as credenciais e o token da conta de teste: fica fora do arquivo.
  const { setup_data: _omit, ...summary } = data;
  if (__ENV.SUMMARY_FILE) out[__ENV.SUMMARY_FILE] = JSON.stringify(summary, null, 2);
  return out;
}
