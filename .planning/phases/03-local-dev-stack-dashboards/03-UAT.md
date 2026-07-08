---
status: testing
phase: 03-local-dev-stack-dashboards
source: [03-VERIFICATION.md]
started: 2026-07-08T21:05:00Z
updated: 2026-07-08T21:05:00Z
---

## Current Test

number: 1
name: With stack running, confirm Service Down appears in Grafana Alerting before stopping API
expected: |
  Service Down rule is listed and not Firing during healthy operation
awaiting: user response

## Tests

### 1. Service Down rule visible before demo
expected: Service Down rule is listed in Grafana → Alerting → Alert rules and not Firing during healthy operation
result: [pending]

### 2. Alert transitions to Firing after API stop
expected: Run `docker compose stop app`, wait 60–90s; Service Down transitions to Firing in Grafana Alerting UI
result: [pending]

### 3. Alert recovery and no false firing on boot
expected: After `docker compose start app`, alert returns to Normal within ~60s; fresh `docker compose up` does not false-fire during model load
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
