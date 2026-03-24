#!/usr/bin/env python3
"""
Celery Worker 健康检查脚本
用于 Docker 健康检查和监控
"""
import sys
import os
import subprocess
import redis
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_redis_connection(host: str = "localhost", port: int = 6379, db: int = 1) -> bool:
    """检查 Redis 连接"""
    try:
        client = redis.Redis(host=host, port=port, db=db, socket_timeout=5)
        client.ping()
        return True
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return False


def check_celery_worker_status() -> bool:
    """检查 Celery Worker 状态"""
    try:
        # 使用 celery -A scheduler inspect ping 检查
        result = subprocess.run(
            ["celery", "-A", "scheduler", "inspect", "ping", "-d", "celery@*"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # 如果有响应，则认为 worker 健康
        if "pong" in result.stdout.lower() or result.returncode == 0:
            return True

        print(f"Celery inspect failed: {result.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print("Celery inspect timeout")
        return False
    except Exception as e:
        print(f"Celery health check error: {e}")
        return False


def check_disk_space(path: str = "/app", min_percent: float = 10.0) -> bool:
    """检查磁盘空间"""
    try:
        stat = os.statvfs(path)
        percent = (stat.f_bavail * 100) / stat.f_blocks
        if percent < min_percent:
            print(f"Disk space low: {percent:.1f}% available")
            return False
        return True
    except Exception as e:
        print(f"Disk check error: {e}")
        return True  # 磁盘检查失败不阻塞


def main():
    """主健康检查函数"""
    checks_passed = 0
    checks_total = 3

    # 从环境变量获取 Redis 配置
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB_CELERY_BROKER", "1"))

    print(f"Starting health check...")
    print(f"Redis: {redis_host}:{redis_port}/{redis_db}")

    # 1. 检查 Redis 连接
    if check_redis_connection(redis_host, redis_port, redis_db):
        print("✅ Redis connection: OK")
        checks_passed += 1
    else:
        print("❌ Redis connection: FAILED")

    # 2. 检查 Celery Worker 状态
    if check_celery_worker_status():
        print("✅ Celery Worker: OK")
        checks_passed += 1
    else:
        print("❌ Celery Worker: FAILED")

    # 3. 检查磁盘空间
    if check_disk_space():
        print("✅ Disk space: OK")
        checks_passed += 1
    else:
        print("❌ Disk space: LOW")

    print(f"\nHealth check: {checks_passed}/{checks_total} passed")

    # 至少 Redis 连接必须成功
    if checks_passed >= 2:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
