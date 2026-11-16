import http from 'k6/http';
import { check, sleep, fail } from 'k6';

const base = (__ENV.BASE_URL || 'http://gateway:8080').replace(/\/$/, '');
const profile = __ENV.LOAD_PROFILE || 'smoke';
const maxVus = Number(__ENV.MAX_VUS || 30);
if (!['smoke', 'ramp'].includes(profile) || !Number.isInteger(maxVus) || maxVus < 1 || maxVus > 500) {
  throw new Error('Use LOAD_PROFILE=smoke|ramp and MAX_VUS between 1 and 500');
}

export const options = {
  scenarios: profile === 'ramp' ? {
    store: {
      executor: 'ramping-vus', startVUs: 1,
      stages: [{ duration: '1m', target: 5 }, { duration: '2m', target: maxVus },
        { duration: '3m', target: maxVus }, { duration: '1m', target: 0 }],
      gracefulRampDown: '15s',
    },
  } : { store: { executor: 'constant-vus', vus: 1, duration: '15s' } },
  thresholds: {
    'http_req_failed{phase:load}': ['rate<0.01'],
    'http_req_duration{phase:load}': ['p(95)<1000'],
    checks: ['rate>0.99'],
  },
};

function json(response, status) {
  if (response.status !== status) fail(`Setup failed: ${response.request.method} expected ${status}, got ${response.status}`);
  return response.json();
}

export function setup() {
  const nonce = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const headers = { 'Content-Type': 'application/json' };
  const credentials = { email: `load-${nonce}@example.com`, password: `Load-pass-${nonce}` };
  json(http.post(`${base}/auth/register`, JSON.stringify({ name: 'Load test', ...credentials }), { headers }), 201);
  const token = json(http.post(`${base}/auth/login`, JSON.stringify(credentials), { headers }), 200).token;
  const params = { headers: { ...headers, Authorization: `Bearer ${token}` } };
  const product = json(http.post(`${base}/products`, JSON.stringify({ name: 'Load product', price: 10.12, unit: 'kg' }), params), 201);
  const order = json(http.post(`${base}/orders`, JSON.stringify({ items: [{ idProduct: product.id, quantity: 2 }] }), params), 201);
  return { token, productId: product.id, orderId: order.id };
}

export default function (data) {
  const params = { headers: { Authorization: `Bearer ${data.token}` }, tags: { phase: 'load', name: 'GET /products/:id' } };
  const product = http.get(`${base}/products/${data.productId}`, params);
  check(product, { 'product returns 200': r => r.status === 200 });
  params.tags.name = 'GET /orders/:id';
  const order = http.get(`${base}/orders/${data.orderId}`, params);
  check(order, { 'order returns 200': r => r.status === 200 });
  // Identical currencies exercise exchange without flooding its public provider.
  params.tags.name = 'GET /exchanges/USD/USD';
  check(http.get(`${base}/exchanges/USD/USD`, params), { 'exchange returns 200': r => r.status === 200 });
  sleep(0.1);
}

export function teardown(data) {
  check(http.del(`${base}/products/${data.productId}`, null,
    { headers: { Authorization: `Bearer ${data.token}` } }), { 'cleanup returns 204': r => r.status === 204 });
}

export function handleSummary(data) {
  const count = data.metrics.http_reqs?.values.count || 0;
  const duration = data.metrics['http_req_duration{phase:load}']?.values['p(95)'];
  const failures = data.metrics['http_req_failed{phase:load}']?.values.rate;
  return { '/results/k6-summary.json': JSON.stringify(data, null, 2),
    stdout: `Profile=${profile}; requests=${count}; load p95=${duration === undefined ? 'unavailable' : duration.toFixed(2) + 'ms'}; failure rate=${failures ?? 'unavailable'}\nResults: /results/k6-summary.json\n`
      + (__ENV.SUMMARY_STDOUT === 'true' ? `SUMMARY_JSON=${JSON.stringify(data)}\n` : '') };
}
