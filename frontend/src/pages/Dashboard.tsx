import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Card, Statistic, Button, Typography, Skeleton, Alert } from 'antd'
import { UnorderedListOutlined, SettingOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { useRecentEntries } from '../hooks/useEntries'
import { useFeeds } from '../hooks/useFeeds'
import { getLLMStatus } from '../client-api/entries'
import { useReader } from '../context/ReaderContext'

const { Title, Text } = Typography

interface LLMStatus {
  available: boolean
  provider: string
  model: string
  error?: string
  usage: {
    input_tokens: number
    output_tokens: number
    total_tokens: number
    requests: number
    limit: number
  }
}

export function Dashboard() {
  const { t } = useTranslation()
  const { data: entries, isLoading: entriesLoading } = useRecentEntries()
  const { data: feeds, isLoading: feedsLoading } = useFeeds()
  const { readEntryIds, syncStateFromEntries } = useReader()
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null)

  useEffect(() => {
    if (entries) syncStateFromEntries(entries)
  }, [entries, syncStateFromEntries])

  useEffect(() => {
    getLLMStatus().then(setLlmStatus).catch(() => setLlmStatus(null))
  }, [])

  const recentEntries = entries?.slice(0, 5) ?? []
  const unreadCount = entries?.filter(e => !readEntryIds.has(e.id)).length ?? 0
  const feedCount = feeds?.length ?? 0

  return (
    <div>
      {llmStatus && (
        <Alert
          message={llmStatus.available ? `${llmStatus.provider} (${llmStatus.model})` : 'LLM Offline'}
          description={llmStatus.available && llmStatus.usage ? `📊 ${t('dashboard.todayUsage', { tokens: llmStatus.usage.total_tokens.toLocaleString(), requests: llmStatus.usage.requests })}` : llmStatus.error}
          type={llmStatus.available ? 'success' : 'error'}
          showIcon
          icon={llmStatus.available ? <ClockCircleOutlined /> : <SettingOutlined />}
          style={{ marginBottom: 24 }}
        />
      )}

      <Title level={3} style={{ marginBottom: 24 }}>{t('dashboard.title')}</Title>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 24 }}>
        <Card size="small">
          <Statistic title={t('dashboard.articles')} value={unreadCount} />
        </Card>
        <Card size="small">
          <Statistic title={t('dashboard.feeds')} value={feedCount} />
        </Card>
      </div>

      <div style={{ marginBottom: 24, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Link to="/feeds">
          <Button type="primary" icon={<UnorderedListOutlined />}>{t('nav.feeds')}</Button>
        </Link>
        <Link to="/settings">
          <Button icon={<SettingOutlined />}>{t('nav.settings')}</Button>
        </Link>
      </div>

      {entriesLoading || feedsLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} active paragraph={{ rows: 2 }} />
          ))}
        </div>
      ) : recentEntries.length > 0 ? (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Text strong style={{ fontSize: 16 }}>{t('nav.recent')}</Text>
            <Link to="/recent" style={{ fontSize: 13, color: '#2563eb' }}>
              {t('dashboard.viewAll')} →
            </Link>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
            {recentEntries.map((entry) => (
              <Link key={entry.id} to={`/read/${entry.id}`} style={{ textDecoration: 'none' }}>
                <Card size="small" hoverable style={{ borderRadius: 12, opacity: readEntryIds.has(entry.id) ? 0.6 : 1 }}>
                  <div style={{ display: 'flex', gap: 12 }}>
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: 8,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 700,
                        fontSize: 14,
                        flexShrink: 0,
                        background: (entry.total_score ?? 0) >= 0.7 ? '#dcfce7' : (entry.total_score ?? 0) >= 0.4 ? '#fef3c7' : '#f3f4f6',
                        color: (entry.total_score ?? 0) >= 0.7 ? '#15803d' : (entry.total_score ?? 0) >= 0.4 ? '#b45309' : '#6b7280',
                      }}
                    >
                      {Math.round((entry.total_score ?? 0) * 100)}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {entry.title}
                      </Text>
                      <div style={{ fontSize: 12, color: '#6b7280' }}>
                        {entry.feed_name && <Text type="secondary" style={{ fontSize: 12 }}>{entry.feed_name}</Text>}
                        {entry.published_at && (
                          <Text type="secondary" style={{ fontSize: 12 }}> · {new Date(entry.published_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}</Text>
                        )}
                      </div>
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      ) : (
        <Card size="small" style={{ textAlign: 'center', padding: 40 }}>
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>📭 {t('dashboard.noArticles')}</Text>
          <Link to="/onboarding">
            <Button type="primary">{t('dashboard.addFirstFeed')}</Button>
          </Link>
        </Card>
      )}
    </div>
  )
}