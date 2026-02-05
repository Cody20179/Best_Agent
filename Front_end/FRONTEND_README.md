# Best Agent 前端

多對話 AI Agent 系統的 React 前端。

## ✨ 功能特性

### 1. **多對話管理** 🗣️
- 支持建立和切換多個獨立對話
- 每個對話有獨立的編號和記憶
- 實時顯示對話統計信息

### 2. **記憶管理** 💾
- 查看對話記憶（支持按類型篩選）
- 搜索對話中的消息
- 清除特定對話或全部記憶
- 系統記憶查詢和管理

### 3. **模型選擇** 🤖
- 列出所有可用模型
- 動態切換模型
- 實時顯示當前使用的模型

### 4. **響應式設計** 📱
- 深色/淺色主題切換
- 響應式布局
- 流暢的動畫效果

## 🚀 快速開始

### 環境要求
- Node.js 16+
- npm 或 yarn

### 安裝依賴
```bash
npm install
```

### 開發環境
```bash
npm run dev
```

### 生產環境構建
```bash
npm run build
```

## 🔧 配置

編輯 `.env.local` 文件配置 API 地址：

```
VITE_API_BASE_URL=http://localhost:5555
```

## 📁 項目結構

```
src/
├── App.jsx          # 主應用組件
├── App.css          # 樣式文件
├── api.js           # API 服務層
├── main.jsx         # 入口文件
└── index.css        # 全局樣式
```

## 🎯 主要 API 端點

### 對話操作
- `POST /chat/ask` - 提問
- `POST /chat/switch` - 切換對話
- `POST /chat/new` - 建立新對話
- `GET /chat/current` - 當前對話

### 記憶查詢
- `GET /memory/conversations` - 列表
- `GET /memory/messages/{id}` - 查詢消息
- `GET /memory/statistics/{id}` - 統計
- `DELETE /memory/clear/{id}` - 清除

### 模型選擇
- `GET /models/list` - 可用模型
- `POST /models/select` - 選擇模型

## 🎨 主題系統

支持深色和淺色主題，通過 CSS 變數實現：
- `--panel` - 面板背景
- `--text` - 文字顏色
- `--line` - 邊框顏色
- `--muted` - 淡色文字
- `--bubble-me` - 用戶消息泡泡
- `--bubble-them` - AI 消息泡泡

## 📝 使用說明

### 開始對話
1. 在輸入框輸入內容
2. 點擊「送出」按鈕或按 Enter
3. 等待 AI 回覆

### 切換對話
1. 在左側邊欄選擇需要的對話
2. 消息歷史會自動加載

### 建立新對話
1. 點擊側邊欄「➕ 新對話」按鈕
2. 新對話會自動分配編號

### 查看記憶
1. 點擊「💾 記憶」按鈕
2. 查看統計、搜索或清除記憶

### 選擇模型
1. 點擊「🤖 模型」按鈕
2. 從列表中選擇模型

## 🔐 錯誤處理

- 網絡錯誤會顯示錯誤提示
- API 超時會提醒用戶
- 所有操作都有加載狀態指示

## 📱 響應式設計

在小屏幕上會隱藏側邊欄，點擊菜單按鈕展開。

## 🛠️ 故障排查

### API 連接失敗
確保後端服務已啟動：
```bash
# 後端啟動
cd ../Agent
python main.py
```

### 模型列表為空
檢查 Ollama 服務是否正確配置

### 消息加載失敗
刷新頁面或檢查對話編號是否有效

## 📄 許可證

MIT License
