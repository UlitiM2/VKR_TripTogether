import { useState, useEffect, useRef } from 'react'
import { getMessages, sendMessage, getChatWebSocketUrl, type Message } from '../api/chat'
import { useAuth } from '../context/AuthContext'

export function TripChat({ tripId }: { tripId: string }) {
  const { user } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const listRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  async function load() {
    try {
      const { data } = await getMessages(tripId)
      setMessages(data)
    } catch {
      setMessages([])
    } finally {
      setLoading(false)
    }
  }

  function appendUniqueMessage(next: Message) {
    setMessages((prev) => {
      if (prev.some((m) => m.id === next.id)) return prev
      return [...prev, next]
    })
  }

  useEffect(() => {
    load()
  }, [tripId])

  useEffect(() => {
    const url = getChatWebSocketUrl(tripId)
    const ws = new WebSocket(url)
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as Message
        appendUniqueMessage(msg)
      } catch {
        // ignore
      }
    }
    ws.onclose = () => {
      wsRef.current = null
    }
    wsRef.current = ws
    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [tripId])

  useEffect(() => {
    listRef.current?.scrollTo(0, listRef.current.scrollHeight)
  }, [messages])

  async function handleSend(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text) return
    setInput('')
    try {
      const { data } = await sendMessage(tripId, text)
      appendUniqueMessage(data)
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) return <div className="loading">Загрузка...</div>

  return (
    <div className="card board-widget board-widget--chat">
      <h2>Чат</h2>
      <div ref={listRef} className="chat-thread-simple">
        {messages.map((m) => (
          <div key={m.id} className={`chat-msg-simple ${user?.id === m.author_user_id ? 'chat-msg-simple--own' : ''}`}>
            <span className="chat-msg-simple__meta">
              {new Date(m.created_at).toLocaleString()} ({m.author_user_id.slice(0, 8)}…)
            </span>
            <div className="chat-msg-simple__body">{m.content}</div>
          </div>
        ))}
      </div>
      <form className="chat-compose-simple" onSubmit={handleSend}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Сообщение..."
          required
        />
        <button type="submit" className="btn btn-compact">Отправить</button>
      </form>
    </div>
  )
}
