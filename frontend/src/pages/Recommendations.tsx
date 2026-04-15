import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useInterestRecommendations, useTrendingRecommendations } from '../hooks/useRecommendations'
import { Link } from 'react-router-dom'
import { Card, Button, Typography, Skeleton, Tag, Empty } from 'antd'

const { Title, Text } = Typography

type Tab = 'interest' | 'trending'

export function Recommendations() {
  const { t } = useTranslation()
  const [tab, setTab] = useState<Tab>('interest')
  const { data: interestRecs, isLoading: interestLoading } = useInterestRecommendations(20)
  const { data: trendingRecs, isLoading: trendingLoading } = useTrendingRecommendations(20)

  const recs = tab === 'interest' ? interestRecs : trendingRecs
  const isLoading = tab === 'interest' ? interestLoading : trendingLoading

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 16 }}>{t('recommendations.title')}</Title>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button type={tab === 'interest' ? 'primary' : 'default'} onClick={() => setTab('interest')}>
            {t('recommendations.forYou')}
          </Button>
          <Button type={tab === 'trending' ? 'primary' : 'default'} onClick={() => setTab('trending')}>
            {t('recommendations.trending')}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} active paragraph={{ rows: 2 }} />
          ))}
        </div>
      ) : recs && recs.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {recs.map((rec) => {
            const score = rec.match_score ?? rec.trending_score ?? 0
            return (
              <Link key={rec.entry_id} to={`/read/${rec.entry_id}`} style={{ textDecoration: 'none' }}>
                <Card size="small" hoverable style={{ borderRadius: 12 }}>
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
                        background: score >= 0.7 ? '#dcfce7' : '#fef3c7',
                        color: score >= 0.7 ? '#15803d' : '#b45309',
                      }}
                    >
                      {Math.round(score * 100)}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {rec.title}
                      </Text>
                      <div style={{ fontSize: 12, color: '#6b7280', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>{rec.feed_name}</Text>
                        {rec.matched_interest && (
                          <>
                            <span>·</span>
                            <Tag color="green" style={{ margin: 0 }}>✓ {rec.matched_interest}</Tag>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </Card>
              </Link>
            )
          })}
        </div>
      ) : (
        <Empty image="✨" description={t('recommendations.noRecommendations')} />
      )}
    </div>
  )
}