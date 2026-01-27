import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

function App() {
  const [theme, setTheme] = useState('dark')
  const [input, setInput] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const formatTime = () => {
    const now = new Date()
    return now.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false })
  }

  const [messages, setMessages] = useState(() => {
    const now = formatTime()
    return [
      { id: 1, from: 'them', text: '嗨！今天想聊點什麼？', time: now },
      { id: 2, from: 'me', text: '想做一個簡單又好看的聊天室窗。', time: now },
      { id: 3, from: 'them', text: '沒問題，我們先做一個清爽版本。', time: now },
      { id: 4, from: 'me', text: '背景和泡泡有點質感就更棒了。', time: now },
    ]
  })

  const nextId = useMemo(() => messages.reduce((max, m) => Math.max(max, m.id), 0) + 1, [messages])
  const chatBodyRef = useRef(null)
  const fileInputRef = useRef(null)

  const countChars = (text) => text.replace(/\s+/g, '').length

  const handleSubmit = (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text) return

    const time = formatTime()
    const userMessage = { id: nextId, from: 'me', text, time }
    const count = countChars(text)
    const thinkingId = nextId + 1
    const thinkingMessage = {
      id: thinkingId,
      from: 'them',
      type: 'thinking',
      time,
      text: '正在處理你的訊息…',
    }

    setMessages((prev) => [...prev, userMessage, thinkingMessage])
    setInput('')

    setTimeout(() => {
      const replyMessage = {
        id: nextId + 2,
        from: 'them',
        text: `你說了 ${count} 個字。`,
        time: formatTime(),
      }

      setMessages((prev) => {
        const withoutThinking = prev.filter((msg) => msg.id !== thinkingId)
        return [...withoutThinking, replyMessage]
      })
    }, 5000)
  }

  const handlePickFile = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const time = formatTime()
    const fileMessage = {
      id: nextId,
      from: 'me',
      type: 'file',
      name: file.name,
      size: file.size,
      time,
    }
    setMessages((prev) => [...prev, fileMessage])
    e.target.value = ''
  }

  useEffect(() => {
    if (!chatBodyRef.current) return
    chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight
  }, [messages])

  return (
    <div className="page">
      <section className={`chat-shell ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <aside className="history-panel">
          <div className="history-header">
            <h2>紀錄</h2>
            <span className="history-sub">最近對話</span>
          </div>
          <div className="history-list">
            <button className="history-item active" type="button">目前的聊天內容</button>
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
                三
              </button>
              <div className="avatar" aria-hidden="true">A</div>
              <div className="chat-title">
                <h1>Amber</h1>
                <p>線上 • 立即回覆</p>
              </div>
            </div>
            <div className="header-actions">
              <button
                className="ghost theme-toggle"
                type="button"
                onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                aria-label="切換明亮或夜晚模式"
              >
                {theme === 'light' ? '夜晚' : '明亮'}
              </button>
              <button className="ghost" type="button">搜尋</button>
              <button className="ghost" type="button">設定</button>
            </div>
          </header>

          <div className="chat-body" ref={chatBodyRef}>
            <div className="day-separator">今天</div>
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`bubble-row ${msg.from === 'me' ? 'is-me' : 'is-them'}`}
              >
                {msg.type === 'thinking' ? (
                  <div className="bubble thinking">
                    <details>
                      <summary>思考中</summary>
                      <p>{msg.text}</p>
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
                    <p>{msg.text}</p>
                    <span className="time">{msg.time}</span>
                  </div>
                )}
              </div>
            ))}
          </div>

          <form className="chat-input" onSubmit={handleSubmit}>
            <button className="icon-btn" type="button" aria-label="加號" onClick={handlePickFile}>＋</button>
            <input
              ref={fileInputRef}
              className="file-input"
              type="file"
              onChange={handleFileChange}
            />
            <input
              type="text"
              placeholder="輸入訊息…"
              aria-label="訊息輸入"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button className="send-btn" type="submit">送出</button>
          </form>
        </div>
      </section>
    </div>
  )
}

export default App
