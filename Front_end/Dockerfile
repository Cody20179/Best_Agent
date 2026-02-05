# ==================== 前端 Dockerfile ====================
# 構建階段
FROM node:20-alpine as builder

WORKDIR /app

# 複製 package 文件
COPY package*.json ./

# 安裝依賴
RUN npm ci

# 複製應用代碼
COPY . .

# 構建應用
RUN npm run build

# ==================== 運行階段
FROM node:20-alpine

WORKDIR /app

# 安裝全局 serve 用於生產服務
RUN npm install -g serve

# 從構建階段複製構建結果
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

# 暴露端口
EXPOSE 5556

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:5556 || exit 1

# 啟動應用
CMD ["serve", "-s", "dist", "-l", "5556"]
