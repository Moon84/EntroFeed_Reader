import { useTranslation } from 'react-i18next'
import { useRecentEntries } from '../hooks/useEntries'
import { EntryCard } from '../components/EntryCard'
import { Skeleton, Empty, Typography } from 'antd'

const { Title, Text } = Typography

export function RecentEntries() {
  const { t } = useTranslation()
  const { data: entries, isLoading } = useRecentEntries()

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>{t('nav.recent')}</Title>
        <Text type="secondary">{entries?.length ?? 0} {t('dashboard.articles')}</Text>
      </div>

      {isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {Array.from({ length: 8 }).map((_, i) => (
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