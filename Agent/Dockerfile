# ==================== 後端 Dockerfile ====================
FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴（使用 freetds 代替 Microsoft ODBC）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    freetds-dev \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY . .

# 複製啟動腳本
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 設置工作目錄權限
RUN mkdir -p ./uploads && chmod -R 755 ./uploads

# 暴露端口
EXPOSE 5555

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:5555/health || exit 1

# 啟動應用
ENTRYPOINT ["/app/entrypoint.sh"]
