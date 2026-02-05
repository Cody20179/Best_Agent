/**
 * API 服務層
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5555'
const RETRY_ATTEMPTS = 3
const RETRY_DELAY = 1000 // ms

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

// 獲取認證令牌
const getAuthToken = () => {
  return localStorage.getItem('token')
}

const handleResponse = async (response) => {
  // 檢查 CORS 和網絡錯誤
  if (!response.ok) {
    const text = await response.text()
    try {
      const data = JSON.parse(text)
      throw new Error(data.error || `API Error: ${response.status}`)
    } catch (e) {
      throw new Error(`API Error: ${response.status} - ${text || response.statusText}`)
    }
  }
  
  const data = await response.json()
  return data
}

// 帶重試機制的 fetch
const fetchWithRetry = async (url, options = {}, attemptCount = 0) => {
  try {
    // 添加認證令牌到請求頭
    const token = getAuthToken()
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    }
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    })
    return response
  } catch (error) {
    if (attemptCount < RETRY_ATTEMPTS) {
      console.warn(`Fetch 失敗，${RETRY_DELAY}ms 後重試 (${attemptCount + 1}/${RETRY_ATTEMPTS})...`)
      await sleep(RETRY_DELAY)
      return fetchWithRetry(url, options, attemptCount + 1)
    }
    throw error
  }
}

// ==================== 認證操作 ====================

export const authAPI = {
  // 登入
  login: async (username, password) => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      return handleResponse(response)
    } catch (error) {
      console.error('login() 失敗:', error)
      throw error
    }
  },

  // 登出
  logout: async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/auth/logout`, { method: 'POST' })
      return handleResponse(response)
    } catch (error) {
      console.error('logout() 失敗:', error)
      throw error
    }
  },

  // 獲取當前用戶信息
  getCurrentUser: async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/auth/me`)
      return handleResponse(response)
    } catch (error) {
      console.error('getCurrentUser() 失敗:', error)
      throw error
    }
  },

  // 獲取用戶的對話列表
  getUserConversations: async (userId = null) => {
    try {
      const url = userId 
        ? `${API_BASE_URL}/auth/conversations?user_id=${userId}`
        : `${API_BASE_URL}/auth/conversations`
      const response = await fetchWithRetry(url)
      return handleResponse(response)
    } catch (error) {
      console.error('getUserConversations() 失敗:', error)
      throw error
    }
  },

  // 獲取對話消息
  getConversationMessages: async (conversationId) => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/auth/messages/${conversationId}`)
      return handleResponse(response)
    } catch (error) {
      console.error('getConversationMessages() 失敗:', error)
      throw error
    }
  },
}

// ==================== 對話操作 ====================

export const chatAPI = {
  // 提問
  ask: async (userPrompt, conversationId = null, maxTurns = 10) => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/ask`, {
        method: 'POST',
        body: JSON.stringify({
          user_prompt: userPrompt,
          conversation_id: conversationId,
          max_turns: maxTurns,
        }),
      })
      return handleResponse(response)
    } catch (error) {
      console.error('ask() 失敗:', error)
      throw error
    }
  },

  // 切換對話
  switchConversation: async (conversationId) => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/switch`, {
        method: 'POST',
        body: JSON.stringify({ conversation_id: conversationId }),
      })
      return handleResponse(response)
    } catch (error) {
      console.error('switchConversation() 失敗:', error)
      throw error
    }
  },

  // 建立新對話
  createNewConversation: async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/new`, {
        method: 'POST',
      })
      return handleResponse(response)
    } catch (error) {
      console.error('createNewConversation() 失敗:', error)
      throw error
    }
  },

  // 獲取當前對話
  getCurrentConversation: async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/current`)
      return handleResponse(response)
    } catch (error) {
      console.error('getCurrentConversation() 失敗:', error)
      throw error
    }
  },
}

// ==================== 記憶查詢 ====================

export const memoryAPI = {
  // 列出所有對話
  listConversations: async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/memory/conversations`)
      return handleResponse(response)
    } catch (error) {
      console.error('listConversations() 失敗:', error)
      throw error
    }
  },

  // 獲取對話記憶
  getMessages: async (conversationId, limit = 50, memoryType = 'chat') => {
    try {
      const response = await fetchWithRetry(
        `${API_BASE_URL}/memory/messages/${conversationId}?limit=${limit}&memory_type=${memoryType}`
      )
      return handleResponse(response)
    } catch (error) {
      console.error('getMessages() 失敗:', error)
      throw error
    }
  },

  // 獲取對話統計
  getStatistics: async (conversationId) => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/memory/statistics/${conversationId}`)
      return handleResponse(response)
    } catch (error) {
      console.error('getStatistics() 失敗:', error)
      throw error
    }
  },

  // 搜索消息
  searchMessages: async (conversationId, keyword, memoryType = 'chat') => {
    try {
      const response = await fetchWithRetry(
        `${API_BASE_URL}/memory/search/${conversationId}?keyword=${encodeURIComponent(keyword)}&memory_type=${memoryType}`
      )
      return handleResponse(response)
    } catch (error) {
      console.error('searchMessages() 失敗:', error)
      throw error
    }
  },

  // 清除對話記憶
  clearMemory: async (conversationId, memoryType = null) => {
    try {
      const url = memoryType
        ? `${API_BASE_URL}/memory/clear/${conversationId}?memory_type=${memoryType}`
        : `${API_BASE_URL}/memory/clear/${conversationId}`
      const response = await fetchWithRetry(url, { method: 'DELETE' })
      return handleResponse(response)
    } catch (error) {
      console.error('clearMemory() 失敗:', error)
      throw error
    }
  },

  // 清除所有記憶
  clearAllMemory: async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/memory/clear-all`, { method: 'DELETE' })
      return handleResponse(response)
    } catch (error) {
      console.error('clearAllMemory() 失敗:', error)
      throw error
    }
  },
}

// ==================== 系統記憶 ====================

export const systemMemoryAPI = {
  // 獲取所有系統記憶
  getAll: async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/system-memory/all`)
      return handleResponse(response)
    } catch (error) {
      console.error('getAll() 失敗:', error)
      throw error
    }
  },

  // 獲取特定系統記憶
  get: async (key) => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/system-memory/${key}`)
      return handleResponse(response)
    } catch (error) {
      console.error('get() 失敗:', error)
      throw error
    }
  },

  // 保存系統記憶
  save: async (key, content, metadata = null) => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/system-memory/save`, {
        method: 'POST',
        body: JSON.stringify({ key, content, metadata }),
      })
      return handleResponse(response)
    } catch (error) {
      console.error('save() 失敗:', error)
      throw error
    }
  },

  // 更新系統記憶
  update: async (key, content = null, metadata = null) => {
    try {
      const url = new URL(`${API_BASE_URL}/system-memory/update/${key}`)
      if (content) url.searchParams.append('content', content)
      if (metadata) url.searchParams.append('metadata', metadata)
      const response = await fetchWithRetry(url, { method: 'PUT' })
      return handleResponse(response)
    } catch (error) {
      console.error('update() 失敗:', error)
      throw error
    }
  },

  // 刪除系統記憶
  delete: async (key) => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/system-memory/${key}`, { method: 'DELETE' })
      return handleResponse(response)
    } catch (error) {
      console.error('delete() 失敗:', error)
      throw error
    }
  },
}

// ==================== 模型選擇 ====================

export const modelAPI = {
  // 列出可用模型
  list: async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/models/list`)
      return handleResponse(response)
    } catch (error) {
      console.error('list() 失敗:', error)
      throw error
    }
  },

  // 選擇模型
  select: async (modelName) => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/models/select`, {
        method: 'POST',
        body: JSON.stringify({ model_name: modelName }),
      })
      return handleResponse(response)
    } catch (error) {
      console.error('select() 失敗:', error)
      throw error
    }
  },

  // 獲取當前模型
  getCurrent: async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/models/current`)
      return handleResponse(response)
    } catch (error) {
      console.error('getCurrent() 失敗:', error)
      throw error
    }
  },
}

// ==================== 配置 ====================

export const configAPI = {
  // 獲取 Agent 設置
  getAgentSettings: async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/config/agent-settings`)
      return handleResponse(response)
    } catch (error) {
      console.error('getAgentSettings() 失敗:', error)
      throw error
    }
  },

  // 獲取支持的記憶類型
  getMemoryTypes: async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/config/memory-types`)
      return handleResponse(response)
    } catch (error) {
      console.error('getMemoryTypes() 失敗:', error)
      throw error
    }
  },
}

// ==================== 文件管理 ====================

export const fileAPI = {
  // 上傳文件
  upload: async (file, conversationId) => {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('conversation_id', conversationId)
      
      const response = await fetch(`${API_BASE_URL}/files/upload`, {
        method: 'POST',
        body: formData,
      })
      
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error('upload() 失敗:', error)
      throw error
    }
  },

  // 獲取對話的所有文件
  getConversationFiles: async (conversationId) => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/files/conversation/${conversationId}`)
      return handleResponse(response)
    } catch (error) {
      console.error('getConversationFiles() 失敗:', error)
      throw error
    }
  },

  // 刪除文件
  delete: async (conversationId, filename) => {
    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/files/${conversationId}/${filename}`, { method: 'DELETE' })
      return handleResponse(response)
    } catch (error) {
      console.error('delete() 失敗:', error)
      throw error
    }
  },
}
