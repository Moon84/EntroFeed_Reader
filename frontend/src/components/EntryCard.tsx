import { Link } from 'react-router-dom'
import type { FeedEntry } from '../types'
import { Card, Typography, Tag } from 'antd'
import { useReader } from '../context/ReaderContext'

const { Text } = Typography

interface EntryCardProps {
  entry: FeedEntry & { feed_name?: string }
}

export function EntryCard({ entry }: EntryCardProps) {
  const { readEntryIds } = useReader()
  const isRead = readEntryIds.has(entry.id)
  const score = entry.total_score ?? 0
  const matchedInterests = entry.matched_interests ?? []

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return dateStr
    }
  }

  const stripHtml = (html: string) => {
    return html.replace(/<[^>]+>/g, '')
  }

  return (
    <Link to={`/read/${entry.id}`} style={{ textDecoration: 'none' }}>
      <Card size="small" hoverable style={{ borderRadius: 12, opacity: isRead ? 0.6 : 1 }}>
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
              background: score >= 0.7 ? '#dcfce7' : score >= 0.4 ? '#fef3c7' : '#f3f4f6',
              color: score >= 0.7 ? '#15803d' : score >= 0.4 ? '#b45309' : '#6b7280',
            }}
          >
            {Math.round(score * 100)}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {entry.title}
            </Text>
            <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>
              {entry.feed_name && <Text type="secondary" style={{ fontSize: 12 }}>{entry.feed_name}</Text>}
              {entry.feed_name && entry.published_at && <span> · </span>}
              {entry.published_at && <Text type="secondary" style={{ fontSize: 12 }}>{formatDate(entry.published_at)}</Text>}
            </div>
            {entry.preview && (
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {stripHtml(entry.preview)}
              </Text>
            )}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {entry.tags?.slice(0, 3).map((tag, i) => (
                <Tag key={`${tag.name}-${i}`} style={{ margin: 0 }}>{tag.name}</Tag>
              ))}
              {matchedInterests.slice(0, 2).map((interest) => (
                <Tag key={interest} color="green" style={{ margin: 0 }}>✓ {interest}</Tag>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </Link>
  )
}