import { useState, useCallback, useRef, useEffect } from 'react'
import { XProvider, Conversations, Sender } from '@ant-design/x'
import { theme, Button, Typography, Card, List } from 'antd'
import { useTranslation } from 'react-i18next'
import { apiGet, apiPostJson } from '../client-api/client'

const { Title, Text } = Typography

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp?: number
}

interface Session {
  id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

const SESSION_STORAGE_KEY = 'entrofeed_agent_session'

export function Agent() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [showSessionList, setShowSessionList] = useState(false)
  const conversationsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadSessions()
    const savedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)
    if (savedSessionId) {
      loadSession(savedSessionId)
    }
  }, [])

  const loadSessions = async () => {
    try {
      const res = await apiGet<{ sessions: Session[] }>('/api/agent/sessions')
      setSessions(res.sessions || [])
    } catch (e) {
      console.error('Failed to load sessions:', e)
    }
  }

  const loadSession = async (sessionId: string) => {
    try {
      const res = await apiGet<{
        id: string
        title: string
        messages: Array<{ role: string; content: string; timestamp?: string }>
      }>(`/api/agent/sessions/${sessionId}`)

      if (res.messages && res.messages.length > 0) {
        const msgs: Message[] = res.messages.map((m, i) => ({
          id: `${m.role}-${i}`,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          timestamp: m.timestamp ? new Date(m.timestamp).getTime() : Date.now(),
        }))
        setMessages(msgs)
        setCurrentSessionId(res.id)
        localStorage.setItem(SESSION_STORAGE_KEY, res.id)
      } else {
        setCurrentSessionId(sessionId)
        setMessages([])
        localStorage.setItem(SESSION_STORAGE_KEY, sessionId)
      }
    } catch (e) {
      console.error('Failed to load session:', e)
    }
  }

  const createNewSession = async () => {
    try {
      const res = await apiPostJson<{ id: string; title: string }>('/api/agent/sessions', {})
      await loadSessions()
      setCurrentSessionId(res.id)
      setMessages([])
      localStorage.setItem(SESSION_STORAGE_KEY, res.id)
      setShowSessionList(false)
    } catch (e) {
      console.error('Failed to create session:', e)
    }
  }

  const deleteSession = async (sessionId: string) => {
    try {
      await fetch(`/api/agent/sessions/${sessionId}`, { method: 'DELETE' })
      await loadSessions()
      if (currentSessionId === sessionId) {
        const remaining = sessions.filter(s => s.id !== sessionId)
        if (remaining.length > 0) {
          await loadSession(remaining[0].id)
        } else {
          await createNewSession()
        }
      }
    } catch (e) {
      console.error('Failed to delete session:', e)
    }
  }

  const clearCurrentSession = async () => {
    if (!currentSessionId) return
    try {
      await apiPostJson(`/api/agent/sessions/${currentSessionId}/clear`, {})
      setMessages([])
      await loadSessions()
    } catch (e) {
      console.error('Failed to clear session:', e)
    }
  }

  const handleSubmit = useCallback(async (value: string) => {
    if (!value.trim()) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: value,
      timestamp: Date.now(),
    }

    setMessages(prev => [...prev, userMessage])
    setLoading(true)
    setInputValue('')

    try {
      const response = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: value, session_id: currentSessionId }),
      })

      const data = await response.json()

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.reply || "I'm sorry, I couldn't process that request.",
        timestamp: Date.now(),
      }

      setMessages(prev => [...prev, assistantMessage])

      if (data.session_id && data.session_id !== currentSessionId) {
        setCurrentSessionId(data.session_id)
        localStorage.setItem(SESSION_STORAGE_KEY, data.session_id)
        loadSessions()
      }
    } catch (error) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your request.',
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }, [currentSessionId])

  const chatMessages = messages.map(msg => ({
    key: msg.id,
    role: msg.role as 'user' | 'assistant',
    content: msg.content,
  }))

  useEffect(() => {
    if (conversationsRef.current) {
      conversationsRef.current.scrollTop = conversationsRef.current.scrollHeight
    }
  }, [messages])

  const SUGGESTIONS = [
    { label: t('agent.showRecommendations'), value: t('agent.showMyRecommendations') },
    { label: t('agent.trendingArticles'), value: t('agent.whatTrending') },
    { label: t('agent.dailyDigest'), value: t('agent.generateDigest') },
    { label: t('agent.manageInterests'), value: t('agent.helpManageInterests') },
    { label: t('agent.translateArticle'), value: t('agent.translateToChinese') },
  ]

  const currentSession = sessions.find(s => s.id === currentSessionId)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>{t('nav.agent', 'AI Assistant')}</Title>
          <Text type="secondary">{currentSession?.title || t('agent.newChat', 'New Chat')}</Text>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button onClick={() => setShowSessionList(!showSessionList)}>
            📋 {t('agent.sessions', 'Sessions')}
          </Button>
          <Button type="primary" onClick={createNewSession}>
            + {t('agent.newChat', 'New')}
          </Button>
        </div>
      </div>

      {showSessionList && (
        <Card size="small" style={{ marginBottom: 16 }} bodyStyle={{ padding: 0 }}>
          <List
            size="small"
            locale={{ emptyText: t('agent.noSessions', 'No sessions') }}
            dataSource={sessions}
            renderItem={(session) => (
              <List.Item
                style={{
                  padding: '12px 16px',
                  cursor: 'pointer',
                  background: session.id === currentSessionId ? '#eff6ff' : 'transparent',
                }}
                onClick={() => { loadSession(session.id); setShowSessionList(false) }}
                extra={
                  <Button size="small" danger onClick={(e) => { e.stopPropagation(); deleteSession(session.id) }}>
                    🗑️
                  </Button>
                }
              >
                <List.Item.Meta
                  title={session.title}
                  description={`${session.message_count} ${t('agent.messages', 'messages')}`}
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      <Card style={{ flex: 1, overflow: 'hidden' }} bodyStyle={{ display: 'flex', flexDirection: 'column', height: '100%', padding: 0 }}>
        <XProvider
          theme={{ algorithm: theme.defaultAlgorithm, token: { colorPrimary: '#2563eb' } }}
        >
          <div style={{ flex: 1, overflow: 'auto', padding: 16 }} ref={conversationsRef}>
            {messages.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>🤖</div>
                <Title level={4} style={{ marginBottom: 8 }}>{t('agent.title')}</Title>
                <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
                  {t('agent.placeholder')}
                </Text>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                  {SUGGESTIONS.map((s) => (
                    <Button key={s.value} onClick={() => handleSubmit(s.value)}>
                      {s.label}
                    </Button>
                  ))}
                </div>
              </div>
            ) : (
              <Conversations items={chatMessages} />
            )}
          </div>

          {messages.length > 0 && (
            <div style={{ padding: '8px 16px', borderTop: '1px solid #e5e7eb' }}>
              <Button size="small" onClick={clearCurrentSession}>
                🗑️ {t('agent.clear', 'Clear')}
              </Button>
            </div>
          )}

          <div style={{ padding: '12px 16px', borderTop: '1px solid #e5e7eb' }}>
            <Sender
              value={inputValue}
              onChange={setInputValue}
              onSubmit={handleSubmit}
              loading={loading}
              placeholder={t('agent.placeholder', 'Ask me about your feeds, recommendations...')}
            />
          </div>
        </XProvider>
      </Card>
    </div>
  )
}