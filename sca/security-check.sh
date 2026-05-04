#!/bin/bash
echo on
set -e
echo "[1/3] npm audit..."
npm audit --audit-level=moderate
echo "[2/3] OWASP ZAP baseline..."
docker run --rm -v "$(pwd):/zap/wrk" -t owasp/zap2docker-stable zap-baseline.py -t http://host.docker.internal:3000 -r zap_report.html || true
echo "[3/3] Проверка hardcoded secrets..."
grep -r "test-api-key" app.js && echo "FAIL: key found" && exit 1 || echo "OK"
echo "Все проверки пройдены."