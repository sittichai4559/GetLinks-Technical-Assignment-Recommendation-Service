import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {

    cache_miss_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 10 },
        { duration: '30s', target: 30 },
        { duration: '10s', target: 0 },
      ],
      exec: 'cacheMiss',
    },

    cache_hit_test: {
      executor: 'constant-vus',
      vus: 20,
      duration: '30s',
      exec: 'cacheHit',
    },

    batch_endpoint_test: {
      executor: 'constant-vus',
      vus: 10,
      duration: '20s',
      exec: 'batchEndpoint',
    },

  },
};

const BASE_URL = 'http://localhost:8080';

export function cacheMiss() {

  // random user -> likely cache miss
  const userId = Math.floor(Math.random() * 20) + 1;

  const res = http.get(`${BASE_URL}/users/${userId}/recommendations`);

  check(res, {
    'cache miss status 200': (r) => r.status === 200,
    'response time < 800ms': (r) => r.timings.duration < 800,
  });

  sleep(1);
}

export function cacheHit() {

  // same user -> redis cache hit
  const res = http.get(`${BASE_URL}/users/1/recommendations`);

  check(res, {
    'cache hit status 200': (r) => r.status === 200,
    'fast response < 200ms': (r) => r.timings.duration < 200,
  });

  sleep(0.5);
}

export function batchEndpoint() {

  const page = Math.floor(Math.random() * 5) + 1;

  const res = http.get(`${BASE_URL}/recommendations/batch?page=${page}&limit=10`);

  check(res, {
    'batch status 200': (r) => r.status === 200,
    'batch response < 1500ms': (r) => r.timings.duration < 1500,
  });

  sleep(1);
}