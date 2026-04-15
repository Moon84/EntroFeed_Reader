import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { getEntryContent } from '../api/entries'
import { useSimilarRecommendations } from '../hooks/useRecommendations'
import { Card, Typography, Button, Skeleton, Alert, Tag, List } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

export function ArticleReader() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const { data: similar } = useSimilarRecommendations(id!, 5)

  const { data: result, isLoading } = useQuery({
    queryKey: ['entry', id],
    queryFn: () => getEntryContent(id!),
    enabled: !!id,
  })

  const content = result?.content as {
    title?: string
    feed_name?: string
    published_at?: string
    word_count?: number
    reading_time?: number
    unretrievable?: boolean
    url?: string
    content?: string
    preview?: string
  } | undefined

  if (isLoading) {
    return (
      <div>
        <Skeleton active paragraph={{ rows: 8 }} />
      </div>
    )
  }

  if (!content) {
    return (
      <Card size="small" style={{ textAlign: 'center', padding: 40 }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>📄 {t('dashboard.noArticles')}</Text>
        <Link to="/">
          <Button type="primary" icon={<ArrowLeftOutlined />}>{t('article.back')}</Button>
        </Link>
      </Card>
    )
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Link to="/" style={{ fontSize: 13, color: '#6b7280', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 16 }}>
          <ArrowLeftOutlined /> {t('article.back')}
        </Link>
        <Title level={2} style={{ marginBottom: 12 }}>{content.title}</Title>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 14, color: '#6b7280', flexWrap: 'wrap' }}>
          {content.feed_name && <Text type="secondary">{content.feed_name}</Text>}
          {content.published_at && <Text type="secondary">{formatDate(content.published_at)}</Text>}
          {content.word_count && <Text type="secondary">{content.word_count} {t('article.words')}</Text>}
          {content.reading_time && <Text type="secondary">{content.reading_time} {t('article.minRead')}</Text>}
        </div>
      </div>

      {content.unretrievable && (
        <Alert
          message={t('article.unretrievable')}
          description={
            <a href={content.url} target="_blank" rel="noopener noreferrer" style={{ color: 'inherit' }}>
              {t('article.readMore')}
            </a>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 20 }}
        />
      )}

      <Card size="small" style={{ marginBottom: 24 }}>
        <div dangerouslySetInnerHTML={{ __html: content.content || content.preview || '' }} style={{ lineHeight: 1.8 }} />
      </Card>

      {similar && similar.length > 0 && (
        <Card title={t('article.similar')} size="small">
          <List
            size="small"
            dataSource={similar}
            renderItem={(rec) => {
              const score = rec.similarity_score ?? 0
              return (
                <List.Item>
                  <Link to={`/read/${rec.entry_id}`} style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%' }}>
                    <Tag color={score >= 0.7 ? 'green' : 'orange'} style={{ flexShrink: 0 }}>
                      {Math.round(score * 100)}%
                    </Tag>
                    <Text ellipsis style={{ flex: 1 }}>{rec.title}</Text>
                  </Link>
                </List.Item>
              )
            }}
          />
        </Card>
      )}
    </div>
  )
}