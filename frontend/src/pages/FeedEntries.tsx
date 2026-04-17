import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useEntries } from '../hooks/useEntries'
import { useFeeds } from '../hooks/useFeeds'
import { useReader } from '../context/ReaderContext'
import { EntryCard } from '../components/EntryCard'
import { Typography, Skeleton, Empty } from 'antd'

const { Title, Text } = Typography

export function FeedEntries() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const { data: feeds } = useFeeds()
  const { data: entries, isLoading } = useEntries(id)
  const { syncStateFromEntries } = useReader()

  const feed = feeds?.find((f) => f.id === id)

  useEffect(() => {
    if (entries) syncStateFromEntries(entries)
  }, [entries, syncStateFromEntries])

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>{feed?.name ?? t('dashboard.feeds')}</Title>
        {feed && (
          <Text type="secondary" style={{ fontSize: 12 }}>{feed.url}</Text>
        )}
        <Text type="secondary" style={{ display: 'block', marginTop: 4 }}>{entries?.length ?? 0} {t('feeds.entries')}</Text>
      </div>

      {isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} active paragraph={{ rows: 2 }} />
          ))}
        </div>
      ) : entries && entries.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {entries.map((entry) => (
            <EntryCard key={entry.id} entry={entry} />
          ))}
        </div>
      ) : (
        <Empty image="📭" description={t('dashboard.noArticles')} />
      )}
    </div>
  )
}