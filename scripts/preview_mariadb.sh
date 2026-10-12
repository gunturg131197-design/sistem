#!/usr/bin/env bash
# Menyiapkan MariaDB LOKAL khusus untuk preview/development di kontainer Emergent.
# (Produksi memakai service `mariadb` di docker-compose Coolify — script ini TIDAK dipakai di sana.)
# Aman dijalankan berulang (idempoten). Data disimpan di /app/.mariadb_data agar tidak hilang saat pod restart.
set -e
DATA=/app/.mariadb_data
SOCK=/run/mysqld/mysqld.sock
DB_NAME="${MARIADB_DATABASE:-trirara}"
DB_USER="${MARIADB_USER:-trirara}"
DB_PASS="${MARIADB_PASSWORD:-trirara_dev}"

if ! command -v mariadbd >/dev/null 2>&1; then
  echo "[mariadb] memasang mariadb-server ..."
  apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mariadb-server >/dev/null
fi
mkdir -p /run/mysqld && chown mysql:mysql /run/mysqld
if [ ! -d "$DATA/mysql" ]; then
  echo "[mariadb] inisialisasi datadir $DATA"
  mkdir -p "$DATA" && chown -R mysql:mysql "$DATA"
  mariadb-install-db --user=mysql --datadir="$DATA" --skip-test-db >/dev/null
fi
chown -R mysql:mysql "$DATA"

cat > /etc/supervisor/conf.d/mariadb.conf <<EOF
[program:mariadb]
command=/usr/sbin/mariadbd --user=mysql --datadir=$DATA --socket=$SOCK --bind-address=127.0.0.1 --port=3306 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
autostart=true
autorestart=true
priority=5
stdout_logfile=/var/log/supervisor/mariadb.out.log
stderr_logfile=/var/log/supervisor/mariadb.err.log
EOF
supervisorctl reread >/dev/null && supervisorctl update >/dev/null || true
supervisorctl start mariadb >/dev/null 2>&1 || true
for i in $(seq 1 30); do mariadb -uroot --socket=$SOCK -e "SELECT 1" >/dev/null 2>&1 && break; sleep 1; done
mariadb -uroot --socket=$SOCK <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
CREATE USER IF NOT EXISTS '$DB_USER'@'127.0.0.1' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL
echo "[mariadb] siap: mysql://$DB_USER:***@127.0.0.1:3306/$DB_NAME"
