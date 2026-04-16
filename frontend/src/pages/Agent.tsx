import { useState, useCallback, useRef, useEffect } from 'react'
import { XProvider, Conversations, Sender } from '@ant-design/x'
import { theme, Button, Typography, Card, List, Tag } from 'antd'
import { useTranslation } from 'react-i18next'
import { apiGet, apiPostJson } from '../client-api/client'
import type { FeedEntry } from '../types'

const { Title, Text } = Typography

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp?: number
  attachments?: FeedEntry[]
}

interface Session {
  id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

const SESSION_STORAGE_KEY = 'entrofeed_agent_session'

function AttachmentCard({ entry, onRemove }: { entry: FeedEntry; onRemove?: () => void }) {
  const score = entry.total_score ?? 0
  const scoreColor = score >= 0.7 ? '#15803d' : score >= 0.4 ? '#b45309' : '#6b7280'
  const scoreBg = score >= 0.7 ? '#dcfce7' : score >= 0.4 ? '#fef3c7' : '#f3f4f6'

  return (
    <Card
      size="small"
      style={{ marginBottom: 8, border: '1px solid #e5e7eb', borderRadius: 8 }}
      bodyStyle={{ padding: 12 }}
      extra={onRemove ? <Button size="small" type="text" onClick={onRemove}>×</Button> : undefined}
    >
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
        <div
          style={{
            width: 36, height: 36, borderRadius: 8, display: 'flex',
            alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 11,
            flexShrink: 0, background: scoreBg, color: scoreColor,
          }}
        >
          {Math.round(score * 100)}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {entry.title}
          </div>
          <div style={{ fontSize: 11, color: '#6b7280', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <span>{entry.feed_name || 'Unknown source'}</span>
            {entry.published_at && (
              <>
                <span>·</span>
                <span>{new Date(entry.published_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}</span>
              </>
            )}
            {entry.tags?.slice(0, 3).map((tag, i) => (
              <Tag key={i} style={{ margin: 0, fontSize: 10 }}>{tag.name}</Tag>
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}

function AttachmentSection({ entries, onRemove }: { entries: FeedEntry[]; onRemove?: (id: string) => void }) {
  if (entries.length === 0) return null

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          📎 {entries.length} article{entries.length > 1 ? 's' : ''} selected for analysis
        </Text>
      </div>
      {entries.map(entry => (
        <AttachmentCard
          key={entry.id}
          entry={entry}
          onRemove={onRemove ? () => onRemove(entry.id) : undefined}
        />
      ))}
    </div>
  )
}

export function Agent() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [showSessionList, setShowSessionList] = useState(false)
  const [pendingAttachments, setPendingAttachments] = useState<FeedEntry[]>([])
  const conversationsRef = useRef<HTMLDivElement>(null)
  const pendingArticleSent = useRef(false)

  useEffect(() => {
    loadSessions()
    const savedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)
    if (savedSessionId) {
      loadSession(savedSessionId)
    }

    // Handle pending articles sent from reader
    const pendingIds = localStorage.getItem('entrofeed_pending_articles')
    if (pendingIds && !pendingArticleSent.current) {
      pendingArticleSent.current = true
      localStorage.removeItem('entrofeed_pending_articles')
      const ids: string[] = JSON.parse(pendingIds)
      // Fetch entries for these IDs
      fetchAndAttachEntries(ids)
    }
  }, [])

  const fetchAndAttachEntries = async (ids: string[]) => {
    try {
      // Fetch entries in parallel - use list-feed-entries which returns all, then filter
      const allEntries = await apiGet<FeedEntry[]>('/util/list-feed-entries')
      const matched = allEntries.filter(e => ids.includes(e.id))
      if (matched.length > 0) {
        setPendingAttachments(matched)
      } else {
        // Fallback: try fetching each individually
        const results = await Promise.allSettled(
          ids.map(id => apiGet<FeedEntry>(`/read/${id}?accept=json`).catch(() => null))
        )
        const entries = results
          .filter((r): r is PromiseFulfilledResult<FeedEntry> => r.status === 'fulfilled' && r.value !== null)
          .map(r => r.value)
        if (entries.length > 0) {
          setPendingAttachments(entries)
        }
      }
    } catch (e) {
      console.error('Failed to fetch pending entries:', e)
    }
  }

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

  const buildMessageWithAttachments = (userText: string, attachments: FeedEntry[]): string => {
    if (attachments.length === 0) return userText

    const articlesSection = attachments.map((e, i) =>
      `[Article ${i + 1}]
ID: ${e.id}
Title: ${e.title}
Source: ${e.feed_name || 'Unknown'}
URL: ${e.url}
Published: ${e.published_at}
Score: ${Math.round((e.total_score ?? 0) * 100)}/100
${e.tags?.length ? `Tags: ${e.tags.map(t => t.name).join(', ')}` : ''}
${e.preview ? `Preview: ${e.preview.slice(0, 300)}...` : ''}`
    ).join('\n\n')

    return `I'm sharing ${attachments.length} article${attachments.length > 1 ? 's' : ''} for your analysis:\n\n${articlesSection}\n\n---\n\nMy question/request: ${userText}`
  }

  const handleSubmit = useCallback(async (value: string) => {
    if (!value.trim()) return

    const attachmentsToSend = [...pendingAttachments]
    const messageText = buildMessageWithAttachments(value, attachmentsToSend)

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: messageText,
      timestamp: Date.now(),
      attachments: attachmentsToSend,
    }

    setMessages(prev => [...prev, userMessage])
    setLoading(true)
    setInputValue('')

    // Keep attachments visible (they stay until explicitly removed)
    // Don't clear pendingAttachments - user might want to ask follow-ups about same articles

    try {
      const response = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText, session_id: currentSessionId }),
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
  }, [currentSessionId, pendingAttachments])

  const removeAttachment = (id: string) => {
    setPendingAttachments(prev => prev.filter(e => e.id !== id))
  }

  const clearAttachments = () => {
    setPendingAttachments([])
  }

  // Custom message renderer that shows attachments for user messages
  const chatItems = messages.map(msg => ({
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
            {/* Attachment section */}
            {pendingAttachments.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    📎 {pendingAttachments.length} article{pendingAttachments.length > 1 ? 's' : ''} attached — AI will fetch content automatically
                  </Text>
                  <Button size="small" type="text" onClick={clearAttachments}>Clear all</Button>
                </div>
                <AttachmentSection entries={pendingAttachments} onRemove={removeAttachment} />
              </div>
            )}

            {messages.length === 0 && pendingAttachments.length === 0 ? (
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
              <Conversations items={chatItems} />
            )}
          </div>

          {messages.length > 0 && (
            <div style={{ padding: '8px 16px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: 8 }}>
              <Button size="small" onClick={clearCurrentSession}>
                🗑️ {t('agent.clear', 'Clear')}
              </Button>
              {pendingAttachments.length > 0 && (
                <Button size="small" onClick={clearAttachments}>
                  Clear articles
                </Button>
              )}
            </div>
          )}

          <div style={{ padding: '12px 16px', borderTop: '1px solid #e5e7eb' }}>
            <Sender
              value={inputValue}
              onChange={setInputValue}
              onSubmit={handleSubmit}
              loading={loading}
              placeholder={
                pendingAttachments.length > 0
                  ? 'Ask about the attached articles, or type your question...'
                  : t('agent.placeholder', 'Ask me about your feeds, recommendations...')
              }
            />
          </div>
        </XProvider>
      </Card>
    </div>
  )
}
