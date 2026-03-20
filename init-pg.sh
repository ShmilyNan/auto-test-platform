#!/bin/bash
set -e

# 等待 PostgreSQL 生成默认配置文件
until [ -f "$PGDATA/pg_hba.conf" ]; do
    echo "等待 pg_hba.conf 文件生成..."
    sleep 1
done

echo "正在生成自定义 pg_hba.conf..."

# 备份原文件（可选）
cp "$PGDATA/pg_hba.conf" "$PGDATA/pg_hba.conf.bak"

# 写入新的配置
cat > "$PGDATA/pg_hba.conf" << 'EOF'
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
local   replication     all                                     trust
host    replication     all             127.0.0.1/32            trust
host    replication     all             ::1/128                 trust
host    all             all             all                     trust
# 允许所有外部 IP 使用 md5 密码认证
host    all             all             0.0.0.0/0               md5
EOF

echo "pg_hba.conf 配置完成。"