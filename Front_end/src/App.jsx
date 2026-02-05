import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import { chatAPI, memoryAPI, modelAPI, systemMemoryAPI, authAPI } from './api'
import Login from './Login'

function App() {
  const [theme, setTheme] = useState('dark')
  const [input, setInput] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [loading, setLoading] = useState(false)

  // 用戶認證
  const [user, setUser] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // 對話管理
  const [conversations, setConversations] = useState([])
  const [currentConvId, setCurrentConvId] = useState(1)
  
  // 消息管理
  const [messages, setMessages] = useState([])
  const [uploadedFiles, setUploadedFiles] = useState([])
  
  // 模型管理
  const [models, setModels] = useState([])
  const [currentModel, setCurrentModel] = useState('')
  const [showModelSelector, setShowModelSelector] = useState(false)

  // UI 狀態
  const [showMemoryPanel, setShowMemoryPanel] = useState(false)
  const [showFilesPanel, setShowFilesPanel] = useState(false)
  const [memorySearchKeyword, setMemorySearchKeyword] = useState('')
  const [conversationStats, setConversationStats] = useState(null)

  // 檢查登入狀態
  useEffect(() => {
    const token = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')
    
    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser))
        setIsAuthenticated(true)
      } catch (e) {
        console.error('解析用戶信息失敗:', e)
      }
    }
  }, [])

  const handleLogin = (userData) => {
    setUser(userData)
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    setIsAuthenticated(false)
    setMessages([])
    setConversations([])
  }

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  // 初始化
  useEffect(() => {
    const init = async () => {
      try {
        // 加載當前用戶的對話列表（只加載該用戶的對話）
        try {
          const convRes = await authAPI.getUserConversations()
          setConversations(convRes.conversations || [])
        } catch (error) {
          console.error('加載對話列表失敗:', error)
          setConversations([])
        }
        
        // 加載模型列表
        try {
          const modelRes = await modelAPI.list()
          const modelList = modelRes.models || [modelRes.current_model || 'default']
          setModels(Array.isArray(modelList) ? modelList : [modelRes.current_model || 'default'])
          setCurrentModel(modelRes.current_model || 'default')
        } catch (error) {
          console.error('加載模型列表失敗:', error)
          setModels(['default'])
          setCurrentModel('default')
        }
        
        // 加載當前對話的消息
        try {
          await loadConversationMessages(1)
        } catch (error) {
          console.error('加載對話消息失敗:', error)
          setMessages([])
        }
      } catch (error) {
        console.error('初始化失敗:', error)
      }
    }
    init()
  }, [])

  const formatTime = () => {
    const now = new Date()
    return now.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false })
  }

  // 加載對話消息
  const loadConversationMessages = async (convId) => {
    try {
      // 優先使用用戶隔離的 API
      let res
      try {
        res = await authAPI.getConversationMessages(convId)
      } catch (e) {
        // 如果認證 API 失敗，回退到普通 API（無認證用戶）
        console.log('使用無認證消息 API')
        res = await memoryAPI.getMessages(convId, 100)
      }
      
      const formattedMessages = res.messages.map((msg, idx) => ({
        id: idx,
        from: msg.role === 'user' ? 'me' : 'them',
        text: msg.content,
        time: msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false }) : formatTime(),
      }))
      setMessages(formattedMessages)
      
      // 加載統計信息
      try {
        const statsRes = await memoryAPI.getStatistics(convId)
        setConversationStats(statsRes.statistics)
      } catch (e) {
        console.log('無法加載統計信息:', e)
      }
    } catch (error) {
      console.error('加載消息失敗:', error)
      setMessages([])
    }
  }

  // 切換對話
  const handleSwitchConversation = async (convId) => {
    try {
      setCurrentConvId(convId)
      await chatAPI.switchConversation(convId)
      await loadConversationMessages(convId)
    } catch (error) {
      console.error('切換對話失敗:', error)
    }
  }

  // 建立新對話
  const handleCreateNewConversation = async () => {
    try {
      const res = await chatAPI.createNewConversation()
      setConversations([...conversations, res.conversation_id])
      setCurrentConvId(res.conversation_id)
      setMessages([])
      setConversationStats(null)
    } catch (error) {
      console.error('建立新對話失敗:', error)
    }
  }

  // 提交消息
  const handleSubmit = async (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    setLoading(true)
    const time = formatTime()
    
    // 添加用戶消息
    const userMessage = {
      id: messages.length,
      from: 'me',
      text,
      time,
    }
    
    // 添加思考中的消息
    const thinkingId = messages.length + 1
    const thinkingMessage = {
      id: thinkingId,
      from: 'them',
      type: 'thinking',
      time,
      text: '正在處理你的訊息…',
    }
    
    setMessages((prev) => [...prev, userMessage, thinkingMessage])
    setInput('')

    try {
      // 調用 API
      const res = await chatAPI.ask(text, currentConvId)
      
      // 移除思考消息，添加回覆
      const replyMessage = {
        id: thinkingId,
        from: 'them',
        text: res.response,
        time: formatTime(),
      }
      
      setMessages((prev) => {
        const withoutThinking = prev.filter((msg) => msg.id !== thinkingId)
        return [...withoutThinking, replyMessage]
      })
      
      // 刷新統計
      const statsRes = await memoryAPI.getStatistics(currentConvId)
      setConversationStats(statsRes.statistics)
      
    } catch (error) {
      console.error('提問失敗:', error)
      
      // 移除思考消息，添加錯誤提示
      const errorMessage = {
        id: thinkingId,
        from: 'them',
        text: `抱歉，出現錯誤: ${error.message}`,
        time: formatTime(),
      }
      
      setMessages((prev) => {
        const withoutThinking = prev.filter((msg) => msg.id !== thinkingId)
        return [...withoutThinking, errorMessage]
      })
    } finally {
      setLoading(false)
    }
  }

  // 搜索對話消息
  const handleSearchMessages = async () => {
    if (!memorySearchKeyword.trim()) return
    
    try {
      const res = await memoryAPI.searchMessages(currentConvId, memorySearchKeyword)
      console.log('搜索結果:', res)
      alert(`找到 ${res.total} 條相關消息`)
    } catch (error) {
      console.error('搜索失敗:', error)
    }
  }

  // 選擇模型
  const handleSelectModel = async (modelName) => {
    try {
      await modelAPI.select(modelName)
      setCurrentModel(modelName)
      setShowModelSelector(false)
      alert(`已切換到模型: ${modelName}`)
    } catch (error) {
      console.error('選擇模型失敗:', error)
    }
  }

  // 清除對話記憶
  const handleClearMemory = async () => {
    if (!window.confirm(`確定要清除對話 ${currentConvId} 的所有記憶嗎？`)) return
    
    try {
      await memoryAPI.clearMemory(currentConvId)
      setMessages([])
      setConversationStats(null)
      alert('記憶已清除')
    } catch (error) {
      console.error('清除記憶失敗:', error)
    }
  }

  // 刪除上傳的檔案
  const handleDeleteFile = async (filename) => {
    if (!window.confirm(`確定要刪除檔案 "${filename}" 嗎？`)) return
    
    try {
      await fileAPI.delete(currentConvId, filename)
      setUploadedFiles((prev) => prev.filter((f) => f.filename !== filename))
      alert('檔案已刪除')
    } catch (error) {
      console.error('刪除檔案失敗:', error)
    }
  }

  // 處理文件選擇
  const handleFileClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    // 創建文件消息
    const time = formatTime()
    const fileMessage = {
      id: messages.length,
      from: 'me',
      type: 'file',
      name: file.name,
      size: file.size,
      time,
    }
    
    setMessages((prev) => [...prev, fileMessage])
    
    // 上傳文件到服務器
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('conversation_id', currentConvId)
      
      const response = await fetch('http://localhost:5555/files/upload', {
        method: 'POST',
        body: formData,
      })
      
      const data = await response.json()
      
      if (data.status === 'success') {
        console.log('✓ 文件上傳成功:', data.filename)
        // 可選：添加上傳成功的提示消息
        const successMsg = {
          id: messages.length + 1,
          from: 'them',
          text: `✓ 文件 "${file.name}" 已上傳成功`,
          time: formatTime(),
        }
        setMessages((prev) => [...prev, successMsg])
        setUploadedFiles((prev) => [...prev, { name: file.name, filename: data.filename, size: file.size }])
      }
    } catch (error) {
      console.error('文件上傳失敗:', error)
      const errorMsg = {
        id: messages.length + 1,
        from: 'them',
        text: `✗ 文件上傳失敗: ${error.message}`,
        time: formatTime(),
      }
      setMessages((prev) => [...prev, errorMsg])
    }
    
    // 清空文件輸入
    e.target.value = ''
  }

  const chatBodyRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (!chatBodyRef.current) return
    chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight
  }, [messages])

  // 如果未登入，顯示登入頁面
  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />
  }

  return (
    <div className="page">
      <section className={`chat-shell ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <aside className="history-panel">
          <div className="history-header">
            <h2>紀錄</h2>
            <button 
              className="new-chat-btn" 
              type="button"
              onClick={handleCreateNewConversation}
              title="建立新對話"
            >
              ➕ 新對話
            </button>
          </div>
          
          <div className="history-list">
            {conversations.map((convId) => (
              <button
                key={convId}
                className={`history-item ${currentConvId === convId ? 'active' : ''}`}
                type="button"
                onClick={() => handleSwitchConversation(convId)}
              >
                對話 #{convId}
              </button>
            ))}
          </div>

          <div className="sidebar-footer">
            <button 
              className="ghost-btn" 
              type="button"
              onClick={() => setShowMemoryPanel(!showMemoryPanel)}
              title="記憶管理"
            >
              💾 記憶
            </button>
            <button 
              className="ghost-btn" 
              type="button"
              onClick={() => setShowModelSelector(!showModelSelector)}
              title="選擇模型"
            >
              🤖 模型
            </button>
            <button 
              className="ghost-btn" 
              type="button"
              onClick={() => setShowFilesPanel(!showFilesPanel)}
              title="查看已上傳的檔案"
            >
              📎 檔案
            </button>
            <button 
              className="ghost-btn danger" 
              type="button"
              onClick={handleClearMemory}
              title="清除記憶"
            >
              🗑️ 清除
            </button>
          </div>
        </aside>

        <div className="chat-main">
          <header className="chat-header">
            <div className="header-left">
              <button
                className="menu-btn"
                type="button"
                aria-label="開關紀錄欄"
                onClick={() => setSidebarOpen((prev) => !prev)}
              >
                ☰
              </button>
              <div className="avatar" aria-hidden="true">A</div>
              <div className="chat-title">
                <h1>對話 #{currentConvId}</h1>
                <p>{currentModel && `模型: ${currentModel}`}</p>
              </div>
            </div>
            <div className="header-actions">
              <div className="user-info">
                <span className="user-name">{user?.username}</span>
                <span className={`user-role ${user?.role}`}>{user?.role === 'admin' ? '👑 管理員' : '👤 用戶'}</span>
              </div>
              <button
                className="ghost"
                type="button"
                onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                aria-label="切換明亮或夜晚模式"
              >
                {theme === 'light' ? '🌙' : '☀️'}
              </button>
              <button className="ghost" type="button" onClick={() => setShowMemoryPanel(!showMemoryPanel)}>
                ℹ️ 資訊
              </button>
              <button className="ghost danger" type="button" onClick={handleLogout} title="登出">
                🚪 登出
              </button>
            </div>
          </header>

          <div className="chat-body" ref={chatBodyRef}>
            <div className="day-separator">對話 #{currentConvId}</div>
            {messages.length === 0 ? (
              <div className="empty-state">
                <p>還沒有消息。開始一段對話吧！</p>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`bubble-row ${msg.from === 'me' ? 'is-me' : 'is-them'}`}>
                  {msg.type === 'thinking' ? (
                    <div className="bubble thinking">
                      <details>
                        <summary>思考中...</summary>
                        <p style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</p>
                      </details>
                      <span className="time">{msg.time}</span>
                    </div>
                  ) : msg.type === 'file' ? (
                    <div className="bubble file">
                      <div className="file-card">
                        <div className="file-icon">📄</div>
                        <div>
                          <div className="file-name">{msg.name}</div>
                          <div className="file-meta">{(msg.size / 1024).toFixed(1)} KB</div>
                        </div>
                      </div>
                      <span className="time">{msg.time}</span>
                    </div>
                  ) : (
                    <div className="bubble">
                      <p style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</p>
                      <span className="time">{msg.time}</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          <form className="chat-input" onSubmit={handleSubmit}>
            <button 
              className="file-btn" 
              type="button"
              onClick={handleFileClick}
              aria-label="上傳文件"
              title="上傳文件"
            >
              ＋
            </button>
            <input
              ref={fileInputRef}
              className="file-input"
              type="file"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
            <input
              type="text"
              placeholder="輸入訊息…"
              aria-label="訊息輸入"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button 
              className="send-btn" 
              type="submit"
              disabled={loading}
            >
              {loading ? '⏳' : '送'}
            </button>
          </form>
        </div>
      </section>

      {/* 記憶面板 */}
      {showMemoryPanel && (
        <div className="modal-overlay" onClick={() => setShowMemoryPanel(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>記憶管理</h2>
            
            <div className="modal-section">
              <h3>統計信息</h3>
              {conversationStats ? (
                <div className="stats-grid">
                  <div className="stat-item">
                    <span className="stat-label">總消息</span>
                    <span className="stat-value">{conversationStats.total_messages}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">用戶</span>
                    <span className="stat-value">{conversationStats.user_messages}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">助手</span>
                    <span className="stat-value">{conversationStats.assistant_messages}</span>
                  </div>
                </div>
              ) : (
                <p>加載中...</p>
              )}
            </div>

            <div className="modal-section">
              <h3>搜索消息</h3>
              <div className="search-box">
                <input
                  type="text"
                  placeholder="輸入搜索關鍵詞..."
                  value={memorySearchKeyword}
                  onChange={(e) => setMemorySearchKeyword(e.target.value)}
                />
                <button 
                  className="search-btn"
                  type="button"
                  onClick={handleSearchMessages}
                >
                  搜索
                </button>
              </div>
            </div>

            <button 
              className="close-modal-btn"
              type="button"
              onClick={() => setShowMemoryPanel(false)}
            >
              關閉
            </button>
          </div>
        </div>
      )}

      {/* 模型選擇面板 */}
      {showModelSelector && (
        <div className="modal-overlay" onClick={() => setShowModelSelector(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>選擇模型</h2>
            
            <div className="modal-section">
              <p>當前模型: <strong>{currentModel}</strong></p>
            </div>

            <div className="model-list">
              {Array.isArray(models) && models.length > 0 ? (
                models.map((model) => (
                  <button
                    key={model}
                    className={`model-item ${model === currentModel ? 'active' : ''}`}
                    type="button"
                    onClick={() => handleSelectModel(model)}
                  >
                    {model} {model === currentModel ? '✓' : ''}
                  </button>
                ))
              ) : (
                <p>暫無可用模型，請檢查後端連接</p>
              )}
            </div>

            <button 
              className="close-modal-btn"
              type="button"
              onClick={() => setShowModelSelector(false)}
            >
              關閉
            </button>
          </div>
        </div>
      )}

      {/* 已上傳檔案面板 */}
      {showFilesPanel && (
        <div className="modal-overlay" onClick={() => setShowFilesPanel(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>📎 已上傳檔案</h2>
            
            {uploadedFiles.length === 0 ? (
              <div className="modal-section">
                <p>暫無已上傳的檔案</p>
              </div>
            ) : (
              <div className="files-list-modal">
                {uploadedFiles.map((file) => (
                  <div key={file.filename} className="file-item-modal">
                    <div className="file-info-modal">
                      <span className="file-name-modal">📄 {file.name}</span>
                      <span className="file-size-modal">{(file.size / 1024).toFixed(2)} KB</span>
                    </div>
                    <button
                      className="delete-file-btn-modal"
                      type="button"
                      onClick={() => handleDeleteFile(file.filename)}
                      title="刪除檔案"
                    >
                      ✕ 刪除
                    </button>
                  </div>
                ))}
              </div>
            )}

            <button 
              className="close-modal-btn"
              type="button"
              onClick={() => setShowFilesPanel(false)}
            >
              關閉
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default App

