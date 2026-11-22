# Runbook: checkout Redis cart timeout

## Symptom

Checkout API returns 504 or client timeouts around 3 seconds. Users cannot place
orders. Gateway latency rises while other services look healthy.

## Error fingerprint

`redis_timeout_checkout_cart`

## Likely root cause

`checkout-api` `CartService.load` blocks on Redis `GET cart:{user}` until the
client timeout. When the Redis cart pool is exhausted, the call fails with
`TimeoutError` / `connection pool exhausted`.

## Evidence to collect

1. TraceId for a failing checkout.
2. Confirm an error span on `checkout-api` → `redis-cart`.
3. Confirm Redis pool saturation or elevated Redis latency in the same window.

## Mitigation

1. Fail fast on cart cache misses; do not block the full HTTP timeout.
2. Raise / repair Redis cart connection pool capacity.
3. Shed non-checkout Redis traffic if the pool is shared.

## Do not claim

If the TraceId only shows the gateway hop with no Redis error subtree, say
evidence is insufficient. Do not blame Redis without the fingerprint spans.
