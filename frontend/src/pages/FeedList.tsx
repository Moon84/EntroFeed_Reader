import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Card, Button, Typography, Skeleton, Empty } from 'antd'
import { CloudUploadOutlined, DownloadOutlined, PlusOutlined } from '@ant-design/icons'
import { useFeeds, useImportOpml, useExportOpml } from '../hooks/useFeeds'

const { Title, Text } = Typography

export function FeedList() {
  const { t } = useTranslation()
  const { data: feeds, isLoading } = useFeeds()
  const importOpml = useImportOpml()
  const exportOpml = useExportOpml()
  const fileRef = useRef<HTMLInputElement>(null)

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) importOpml.mutate(file)
  }

  const handleExport = () => {
    exportOpml.mutateAsync().then((blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'entrofeed-feeds.opml'
      a.click()
      URL.revokeObjectURL(url)
    })
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>{t('feeds.title')}</Title>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button icon={<CloudUploadOutlined />} onClick={() => fileRef.current?.click()} loading={importOpml.isPending}>
            {t('feeds.importOpml')}
          </Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport} loading={exportOpml.isPending} disabled={!feeds?.length}>
            {t('feeds.exportOpml')}
          </Button>
          <Link to="/feeds/new">
            <Button type="primary" icon={<PlusOutlined />}>{t('feeds.addFeed')}</Button>
          </Link>
        </div>
      </div>

      <input ref={fileRef} type="file" accept=".opml,.xml" style={{ display: 'none' }} onChange={handleImport} />

      {isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} active paragraph={{ rows: 2 }} />
          ))}
        </div>
      ) : feeds && feeds.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {feeds.map((feed) => (
            <Card key={feed.id} size="small" style={{ borderRadius: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: 8,
                    backgroundColor: '#f3f4f6',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 16,
                    fontWeight: 600,
                  }}
                >
                  {feed.name.charAt(0).toUpperCase()}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text strong style={{ fontSize: 15, display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {feed.name}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {feed.category}
                  </Text>
                </div>
              </div>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {feed.url}
              </Text>
            </Card>
          ))}
        </div>
      ) : (
        <Empty
          image="📡"
          description={t('feeds.noFeeds')}
        >
          <Link to="/onboarding">
            <Button type="primary">{t('dashboard.addFirstFeed')}</Button>
          </Link>
        </Empty>
      )}
    </div>
  )
}