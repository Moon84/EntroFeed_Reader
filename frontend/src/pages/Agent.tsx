import { useState, useCallback, useRef, useEffect } from 'react'
import { XProvider, Bubble, Sender } from '@ant-design/x'
import { theme, Button, Typography, Card, List, Tag, message, Tooltip, Space } from 'antd'
import { CopyOutlined, CheckOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { apiGet, apiPostJson } from '../client-api/client'
import { marked } from 'marked'
import type { FeedEntry } from '../types'
import type { BubbleItemType } from '@ant-design/x'

const { Title, Text, Paragraph } = Typography

interface Session {
  id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

interface AIResponse {
  reply?: string
  success?: boolean
  session_id?: string
  session_title?: string
  sources?: Array<{ title: string; url: string; snippet?: string }>
  thinking?: string
}

const SESSION_STORAGE_KEY = 'entrofeed_agent_session'

marked.setOptions({ breaks: true, gfm: true })

function MarkdownContent({ content }: { content: string }) {
  const html = marked.parse(content) as string
  return (
    <div
      className="agent-markdown"
      style={{ lineHeight: 1.6 }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

function ArticleAttachmentCard({ entry, onRemove }: { entry: FeedEntry; onRemove?: () => void }) {
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

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      message.error('Copy failed')
    }
  }

  return (
    <Tooltip title={copied ? 'Copied!' : 'Copy'}>
      <Button
        size="small"
        type="text"
        icon={copied ? <CheckOutlined /> : <CopyOutlined />}
        onClick={handleCopy}
        style={{ color: copied ? '#52c41a' : undefined }}
      />
    </Tooltip>
  )
}

function SourceItem({ source }: { source: { title: string; url: string; snippet?: string } }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      style={{ display: 'block', padding: '4px 0', fontSize: 12 }}
    >
      <Text strong style={{ fontSize: 12 }}>{source.title}</Text>
      {source.snippet && (
        <Paragraph type="secondary" style={{ fontSize: 11, margin: 0 }} ellipsis={{ rows: 2 }}>
          {source.snippet}
        </Paragraph>
      )}
    </a>
  )
}

export function Agent() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<BubbleItemType[]>([])
  const [inputValue, setInputValue] = useState('')
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [showSessionList, setShowSessionList] = useState(false)
  const [pendingAttachments, setPendingAttachments] = useState<FeedEntry[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const pendingArticleSent = useRef(false)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom()
    }
  }, [messages, scrollToBottom])

  useEffect(() => {
    loadSessions()
    const savedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)
    if (savedSessionId) {
      loadSession(savedSessionId)
    }

    const pendingIds = localStorage.getItem('entrofeed_pending_articles')
    if (pendingIds && !pendingArticleSent.current) {
      pendingArticleSent.current = true
      localStorage.removeItem('entrofeed_pending_articles')
      const ids: string[] = JSON.parse(pendingIds)
      fetchAndAttachEntries(ids)
    }
  }, [])

  const fetchAndAttachEntries = async (ids: string[]) => {
    try {
      const allEntries = await apiGet<FeedEntry[]>('/util/list-feed-entries')
      const matched = allEntries.filter(e => ids.includes(e.id))
      if (matched.length > 0) {
        setPendingAttachments(prev => [...prev, ...matched])
      } else {
        const results = await Promise.allSettled(
          ids.map(id => apiGet<FeedEntry>(`/read/${id}?accept=json`).catch(() => null))
        )
        const entries = results
          .filter((r): r is PromiseFulfilledResult<FeedEntry> => r.status === 'fulfilled' && r.value !== null)
          .map(r => r.value)
        if (entries.length > 0) {
          setPendingAttachments(prev => [...prev, ...entries])
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
        const msgs: BubbleItemType[] = res.messages.map((m, i) => ({
          key: `${m.role}-${i}`,
          role: m.role as 'user' | 'ai',
          content: m.content,
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
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

    const userMessage: BubbleItemType = {
      key: `user-${Date.now()}`,
      role: 'user',
      content: messageText,
      header: timestamp,
      avatar: <UserOutlined />,
      footer: attachmentsToSend.length > 0 ? (
        <div style={{ marginTop: 8 }}>
          {attachmentsToSend.map(entry => (
            <ArticleAttachmentCard key={entry.id} entry={entry} />
          ))}
        </div>
      ) : undefined,
      extra: <CopyButton text={messageText} />,
    }

    setMessages(prev => [...prev, userMessage])
    setLoading(true)
    setInputValue('')

    const loadingKey = `ai-loading-${Date.now()}`
    const loadingMessage: BubbleItemType = {
      key: loadingKey,
      role: 'ai',
      content: '',
      avatar: <RobotOutlined />,
      header: timestamp,
      typing: true,
      loading: true,
    }
    setMessages(prev => [...prev, loadingMessage])

    try {
      const response = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText, session_id: currentSessionId }),
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const data: AIResponse = await response.json()

      const assistantMessage: BubbleItemType = {
        key: `ai-${Date.now()}`,
        role: 'ai',
        content: data.reply || "I'm sorry, I couldn't process that request.",
        header: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        avatar: <RobotOutlined />,
        extra: <CopyButton text={data.reply || ''} />,
        footer: data.sources && data.sources.length > 0 ? (
          <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #f0f0f0' }}>
            <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>Sources:</Text>
            {data.sources.map((s, i) => <SourceItem key={i} source={s} />)}
          </div>
        ) : undefined,
      }

      setMessages(prev => prev.filter(m => m.key !== loadingKey))
      setMessages(prev => [...prev, assistantMessage])

      if (data.session_id && data.session_id !== currentSessionId) {
        setCurrentSessionId(data.session_id)
        localStorage.setItem(SESSION_STORAGE_KEY, data.session_id)
        loadSessions()
      }
    } catch (error) {
      setMessages(prev => prev.filter(m => m.key !== loadingKey))

      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      message.error(`Failed: ${errorMsg}`)
      const errorMessage: BubbleItemType = {
        key: `error-${Date.now()}`,
        role: 'ai',
        content: `Sorry, I encountered an error: ${errorMsg}`,
        header: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        avatar: <RobotOutlined />,
        status: 'error',
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
        <Space>
          <Button onClick={() => setShowSessionList(!showSessionList)}>
            📋 {t('agent.sessions', 'Sessions')}
          </Button>
          <Button type="primary" onClick={createNewSession}>
            + {t('agent.newChat', 'New')}
          </Button>
        </Space>
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
          {pendingAttachments.length > 0 && (
            <div style={{ padding: '12px 16px 0', borderBottom: '1px solid #f0f0f0' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  📎 {pendingAttachments.length} article{pendingAttachments.length > 1 ? 's' : ''} attached
                </Text>
                <Button size="small" type="text" onClick={clearAttachments}>Clear all</Button>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {pendingAttachments.map(entry => (
                  <div key={entry.id} style={{ position: 'relative', width: 200 }}>
                    <ArticleAttachmentCard entry={entry} onRemove={() => removeAttachment(entry.id)} />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
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
              <Bubble.List
                items={messages}
                autoScroll
                role={{
                  ai: {
                    placement: 'start' as const,
                    variant: 'outlined' as const,
                    contentRender: (node: React.ReactNode) => typeof node === 'string' ? <MarkdownContent content={node} /> : node,
                  },
                  user: {
                    placement: 'end' as const,
                    variant: 'filled' as const,
                  },
                }}
              />
            )}
            <div ref={messagesEndRef} />
          </div>

          {messages.length > 0 && (
            <div style={{ padding: '8px 16px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: 8 }}>
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
              placeholder={
                pendingAttachments.length > 0
                  ? 'Ask about the attached articles, or type your question...'
                  : t('agent.placeholder', 'Ask me about your feeds, recommendations...')
              }
            />
          </div>
        </XProvider>
      </Card>

      <style>{`
        .agent-markdown p { margin: 0 0 8px 0; }
        .agent-markdown p:last-child { margin-bottom: 0; }
        .agent-markdown ul, .agent-markdown ol { margin: 0 0 8px 0; padding-left: 20px; }
        .agent-markdown li { margin: 4px 0; }
        .agent-markdown code {
          background: #f5f5f5;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.9em;
        }
        .agent-markdown pre {
          background: #f5f5f5;
          padding: 12px;
          border-radius: 8px;
          overflow-x: auto;
          margin: 8px 0;
        }
        .agent-markdown pre code { background: none; padding: 0; }
        .agent-markdown a { color: #2563eb; }
        .agent-markdown blockquote {
          border-left: 3px solid #d9d9d9;
          margin: 8px 0;
          padding-left: 12px;
          color: #8c8c8c;
        }
      `}</style>
    </div>
  )
}
