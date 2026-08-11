#!/bin/bash
set -e
cd "$(dirname "$0")"



# STEP 1: Build the backend image
# ===============================
sudo docker build -t blnstats-backend ./backend




# STEP 2: Start a throwaway MySQL bootstrapped by mysql/init.sql
# ==============================================================
# Runs on its own docker network with data on tmpfs only; the
# trap removes container and network again however the script
# ends. The upfront cleanup() call clears leftovers of a
# previous crashed run.
cleanup() {
    sudo docker rm -f blnstats-test-mysql >/dev/null 2>&1 || true
    sudo docker network rm blnstats-test >/dev/null 2>&1 || true
}
trap cleanup EXIT
cleanup
sudo docker network create blnstats-test >/dev/null
sudo docker run -d --name blnstats-test-mysql --network blnstats-test --tmpfs /var/lib/mysql \
    -e MYSQL_ROOT_PASSWORD=test -e MYSQL_DATABASE=lnstats \
    -v "$PWD/mysql/init.sql:/docker-entrypoint-initdb.d/init.sql:ro" \
    mysql:9.0.0 >/dev/null




# STEP 3: Wait for the schema bootstrap
# =====================================
# Probing over TCP on purpose: the temporary server the image
# runs WHILE executing init.sql listens on the socket only, so
# a TCP answer means the schema is fully bootstrapped.
echo "Waiting for test MySQL..."
for i in $(seq 90); do
    sudo docker exec blnstats-test-mysql mysql -h127.0.0.1 -uroot -ptest lnstats -e 'SELECT 1' >/dev/null 2>&1 && break
    sleep 1
done




# STEP 4: Run the test suite against the throwaway database
# =========================================================
# Unit tests plus the DB-backed selector tests — the DB_* env
# vars are what backend/blnstats/database/utils.py reads.
sudo docker run --rm --network blnstats-test \
    -e DB_HOST=blnstats-test-mysql -e DB_NAME=lnstats -e DB_USER=root -e DB_PASSWORD=test \
    blnstats-backend python3 -m unittest discover -s tests -p "test_*.py"
