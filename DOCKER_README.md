# Docker Compose 部署指南

## 📋 環境變數說明

### 必填環境變數

| 環境變數 | 說明 | 範例 |
|---------|------|------|
| `MSSQL_SA_PASSWORD` | SQL Server SA 密碼 | `!ok*L9bicP` |
| `MSSQL_HOST` | SQL Server 地址 | `140.134.60.229,5677` |
| `MSSQL_DB` | 數據庫名稱 | `Chat_Memory_DB` |
| `OLLAMA_API_URL` | Ollama API 地址 | `https://ollama.labelnine.app:5016/v1` |
| `OLLAMA_API_KEY` | Ollama API 密鑰 | `ollama-xxx-xxx` |

### Port 配置（必須在 5555~5560 範圍內）

| Port | 服務 | 說明 |
|------|------|------|
| 5555 | 後端 API | FastAPI 服務 |
| 5556 | 前端 | Vite React 應用 |
| 5557 | RAGFlow | 文件處理服務 |
| 1433 | SQL Server | 數據庫（外部不暴露） |

### 可選環境變數

| 環境變數 | 預設值 | 說明 |
|---------|-------|------|
| `TZ` | `Asia/Taipei` | 時區 |
| `RELOAD` | `False` | 是否熱重載（生產設 False） |
| `MSSQL_USER` | `sa` | SQL Server 用戶名 |
| `MSSQL_PORT` | `5677` | SQL Server 連接端口 |

## 🚀 快速開始

### 1. 複製並填寫環境變數

```bash
cp .env.example .env
# 編輯 .env 文件，填寫必要的環境變數
```

### 2. 啟動 Docker Compose

```bash
# 開發模式（顯示日誌）
docker-compose up

# 後台運行（生產模式）
docker-compose up -d
```

### 3. 檢查服務狀態

```bash
# 查看運行中的容器
docker-compose ps

# 查看日誌
docker-compose logs -f back_end
docker-compose logs -f front_end
docker-compose logs -f ms_sql_v1
docker-compose logs -f ragflow
```

### 4. 訪問應用

- **前端**：http://localhost:5556
- **後端 API**：http://localhost:5555
- **RAGFlow**：http://localhost:5557
- **SQL Server**：localhost:1433

## 🔧 常用命令

```bash
# 停止所有服務
docker-compose down

# 重啟特定服務
docker-compose restart back_end

# 查看特定服務日誌
docker-compose logs -f --tail=100 front_end

# 進入容器
docker-compose exec back_end bash
docker-compose exec front_end sh

# 完全清理（包含數據卷）
docker-compose down -v
```

## 🐛 故障排除

### 後端無法連接到 SQL Server

確保在 `.env` 中正確配置 `MSSQL_HOST` 和 `MSSQL_SA_PASSWORD`

```bash
# 測試數據庫連接
docker-compose exec back_end curl -f http://localhost:5555/health
```

### 前端無法連接到後端

檢查 `BACKEND_URL` 環境變數：
- **Docker 內部**：`http://back_end:5555`
- **本地訪問**：`http://localhost:5555`

### RAGFlow 無法啟動

檢查 RAGFlow 日誌：
```bash
docker-compose logs ragflow
```

可能需要更多 memory，修改 docker-compose.yml：
```yaml
ragflow:
  # ...
  deploy:
    resources:
      limits:
        memory: 4G
```

## 📊 健康檢查

所有服務都配備了健康檢查，查看狀態：

```bash
docker-compose ps
# STATUS 顯示 "healthy" 表示服務正常
```

## 🔐 安全建議

1. **生產環境**：更改 `MSSQL_SA_PASSWORD` 為強密碼
2. **API 密鑰**：不要在 `.env` 中硬編碼，使用密鑰管理服務
3. **網絡隔離**：不暴露不必要的 Port
4. **備份數據**：定期備份 `mssql_data` 卷

## 📝 注意事項

- Docker Compose 會自動創建 `best-net-v1` 網絡，容器間可通過容器名通信
- 數據卷 `mssql_data` 會持久化 SQL Server 數據
- 所有 Port 必須在 5555~5560 範圍內
