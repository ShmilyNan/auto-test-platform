# ============================================
# 多阶段构建 - 生产环境优化
# ============================================

# ============================================
# 构建阶段
# ============================================
FROM python:3.14-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================
# 生产阶段
# ============================================
FROM python:3.14-slim AS production
ARG ALLURE_VERSION=2.34.1

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    default-jre-headless \
    unzip \
    ca-certificates \
    && curl -fsSL -o /tmp/allure.zip "https://github.com/allure-framework/allure2/releases/download/${ALLURE_VERSION}/allure-${ALLURE_VERSION}.zip" \
    && unzip /tmp/allure.zip -d /opt/ \
    && ln -s "/opt/allure-${ALLURE_VERSION}/bin/allure" /usr/local/bin/allure \
    && rm -rf /var/lib/apt/lists/* \
    /tmp/allure.zip \
    && apt-get clean

# 从构建阶段复制依赖
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/logs /app/output/reports/allure /app/output/reports/allure-report /app/output/storage  /app/data/celerybeat

# 确保启动脚本有执行权限
RUN chmod +x /app/scripts/*.sh 2>/dev/null || true

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    ENVIRONMENT=prod

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:5000/health', timeout=5.0)" || exit 1

# 暴露端口
EXPOSE 5000

# 启动命令（使用Gunicorn）
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-"]
