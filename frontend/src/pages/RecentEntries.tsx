import { useState, useEffect, useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { apiGet } from '../client-api/client'
import type { FeedEntry } from '../types'
import { useReader } from '../context/ReaderContext'
import { translateText, getLLMStatus } from '../client-api/entries'
import { Button, Select, Typography, Tag, Modal, Spin, Empty, Badge, message, Checkbox } from 'antd'
import { RobotOutlined } from '@ant-design/icons'
import { LikeOutlined, DislikeOutlined, StarFilled, StarOutlined, TranslationOutlined, CheckOutlined } from '@ant-design/icons'
import { Layout as AntLayout } from 'antd'

const { Sider, Content } = AntLayout
const { Title, Text } = Typography

type SortKey = 'time' | 'score'
type FilterKey = 'all' | 'unread'

export function RecentEntries() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const {
    readEntryIds,
    markAsRead,
    markAllAsRead,
    likedEntries,
    toggleLike,
    setDislike,
    favoriteIds,
    toggleFavorite,
    syncStateFromEntries,
  } = useReader()
  const [entries, setEntries] = useState<FeedEntry[]>([])
  const [selectedEntry, setSelectedEntry] = useState<FeedEntry | null>(null)
  const [entryContent, setEntryContent] = useState<Record<string, unknown> | null>(null)
  const [isLoadingContent, setIsLoadingContent] = useState(false)
  const [isLoadingEntries, setIsLoadingEntries] = useState(false)
  const [sortKey, setSortKey] = useState<SortKey>('time')
  const [filterKey, setFilterKey] = useState<FilterKey>('all')
  const [showTranslation, setShowTranslation] = useState(false)
  const [translatedContent, setTranslatedContent] = useState<string | null>(null)
  const [isTranslating, setIsTranslating] = useState(false)
  const [llmAvailable, setLlmAvailable] = useState(true)
  const [selectedEntryIds, setSelectedEntryIds] = useState<Set<string>>(new Set())

  const syncStateRef = useRef(syncStateFromEntries)

  useEffect(() => {
    getLLMStatus().then(status => setLlmAvailable(status.available)).catch(() => setLlmAvailable(false))
  }, [])

  useEffect(() => {
    syncStateRef.current = syncStateFromEntries
  })

  const displayedEntries = useMemo(() => {
    let result = [...entries]
    if (filterKey === 'unread') result = result.filter(e => !readEntryIds.has(e.id))
    if (sortKey === 'score') {
      result.sort((a, b) => (b.total_score ?? 0) - (a.total_score ?? 0))
    } else {
      result.sort((a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime())
    }
    return result
  }, [entries, sortKey, filterKey, readEntryIds])

  useEffect(() => {
    let cancelled = false
    setIsLoadingEntries(true)
    apiGet<FeedEntry[]>('/util/list-feed-entries')
      .then(data => {
        if (cancelled) return
        setEntries(data)
        setIsLoadingEntries(false)
        syncStateRef.current(data)
      })
      .catch(() => {
        if (cancelled) return
        setEntries([])
        setIsLoadingEntries(false)
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!selectedEntry) {
      setEntryContent(null)
      setIsLoadingContent(false)
      return
    }
    markAsRead(selectedEntry.id)
    setIsLoadingContent(true)
    setEntryContent(null)
    let cancelled = false
    apiGet<Record<string, unknown>>(`/read/${selectedEntry.id}?accept=json`)
      .then(data => {
        if (cancelled) return
        setEntryContent(data)
        setIsLoadingContent(false)
      })
      .catch(() => {
        if (cancelled) return
        setEntryContent(null)
        setIsLoadingContent(false)
      })
    return () => { cancelled = true }
  }, [selectedEntry, markAsRead])

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('zh-CN', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    } catch { return dateStr }
  }

  const getLikeState = (entry: FeedEntry) => likedEntries[entry.id] ?? entry.liked ?? 0
  const isFavorited = (entry: FeedEntry) => favoriteIds.has(entry.id) || entry.is_favorite || false

  const handleTranslate = async () => {
    if (!selectedEntry || !entryContent) return
    const content = (entryContent as any)?.content || (entryContent as any)?.preview
    if (!content) return
    const targetLang = i18n.language === 'zh' ? 'zh' : 'en'
    const chineseChars = (content.match(/[\u4e00-\u9fff]/g) || []).length
    const sourceLang = chineseChars / content.length > 0.3 ? 'zh' : 'en'
    if (sourceLang === targetLang) {
      message.info(i18n.language === 'zh' ? '文章已是中文' : 'Article is already in English')
      return
    }
    setIsTranslating(true)
    try {
      const result = await translateText(content, targetLang)
      if (result.success && result.translation) {
        setTranslatedContent(result.translation.text)
        setShowTranslation(true)
      } else if (result.error) {
        message.error(result.error)
      }
    } catch (e) {
      console.error('Translation failed:', e)
    } finally {
      setIsTranslating(false)
    }
  }

  return (
    <AntLayout style={{ height: 'calc(100vh - 48px)', margin: '-24px -32px', overflow: 'hidden' }}>
      {/* Left panel: all entries list */}
      <Sider width={380} style={{ background: '#f7f8fa', borderRight: '1px solid #e5e7eb', height: '100%' }}>
        {/* Wrap all children in a flex column container so flex:1 works */}
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', background: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <Checkbox
                checked={selectedEntryIds.size === displayedEntries.length && displayedEntries.length > 0}
                indeterminate={selectedEntryIds.size > 0 && selectedEntryIds.size < displayedEntries.length}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSelectedEntryIds(new Set(displayedEntries.map(e => e.id)))
                  } else {
                    setSelectedEntryIds(new Set())
                  }
                }}
              />
              <Text strong>{t('nav.recent')}</Text>
              <Badge count={displayedEntries.filter(e => !readEntryIds.has(e.id)).length} style={{ backgroundColor: '#6b7280' }} />
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {selectedEntryIds.size > 0 && (
                <Button size="small" type="primary" icon={<RobotOutlined />} onClick={() => {
                  const ids = Array.from(selectedEntryIds)
                  localStorage.setItem('entrofeed_pending_articles', JSON.stringify(ids))
                  navigate('/agent')
                }}>
                  {selectedEntryIds.size} → AI
                </Button>
              )}
              <Button size="small" type="text" icon={<CheckOutlined />} onClick={() => markAllAsRead(displayedEntries.map(e => e.id))} title={t('article.markAllRead') || 'Mark all as read'} />
            </div>
          </div>
          <div style={{ padding: '8px 16px', background: '#f9fafb', borderBottom: '1px solid #e5e7eb', display: 'flex', gap: 16, flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>{t('article.sort')}:</Text>
              <Select size="small" value={sortKey} onChange={setSortKey} style={{ width: 80 }}>
                <Select.Option value="time">{t('article.byTime')}</Select.Option>
                <Select.Option value="score">{t('article.byScore')}</Select.Option>
              </Select>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>{t('article.filter')}:</Text>
              <Select size="small" value={filterKey} onChange={setFilterKey} style={{ width: 80 }}>
                <Select.Option value="all">{t('article.all')}</Select.Option>
                <Select.Option value="unread">{t('article.unread')}</Select.Option>
              </Select>
            </div>
          </div>
          {/* Entry list - flex:1 with overflow auto */}
          <div style={{ flex: 1, overflowY: 'auto', padding: 8, minHeight: 0 }}>
            {isLoadingEntries ? (
              <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
            ) : displayedEntries.length > 0 ? (
              displayedEntries.map(entry => {
                const isRead = readEntryIds.has(entry.id)
                const likeState = getLikeState(entry)
                const favorited = isFavorited(entry)
                const isImportant = (entry.total_score ?? 0) >= 0.5
                const isSelected = selectedEntry?.id === entry.id

                return (
                  <div
                    key={entry.id}
                    onClick={() => setSelectedEntry(entry)}
                    style={{
                      padding: 12, borderRadius: 8, marginBottom: 4, cursor: 'pointer',
                      background: isSelected ? '#fff' : 'transparent',
                      boxShadow: isSelected ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                      borderLeft: isImportant ? '3px solid #f59e0b' : '3px solid transparent',
                      opacity: isRead ? 0.6 : 1,
                    }}
                  >
                    <div style={{ display: 'flex', gap: 12 }}>
                      <Checkbox
                        checked={selectedEntryIds.has(entry.id)}
                        onChange={(e) => {
                          e.stopPropagation()
                          setSelectedEntryIds(prev => {
                            const next = new Set(prev)
                            if (e.target.checked) next.add(entry.id)
                            else next.delete(entry.id)
                            return next
                          })
                        }}
                        onClick={(e) => e.stopPropagation()}
                        style={{ flexShrink: 0 }}
                      />
                      <div
                        onClick={() => setSelectedEntry(entry)}
                        style={{
                          width: 36, height: 36, borderRadius: 8, display: 'flex',
                          alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 12,
                          flexShrink: 0,
                          background: (entry.total_score ?? 0) >= 0.7 ? '#dcfce7' : (entry.total_score ?? 0) >= 0.4 ? '#fef3c7' : '#f3f4f6',
                          color: (entry.total_score ?? 0) >= 0.7 ? '#15803d' : (entry.total_score ?? 0) >= 0.4 ? '#b45309' : '#6b7280',
                          cursor: 'pointer',
                        }}
                      >
                        {isImportant && <StarOutlined style={{ fontSize: 10, marginRight: 2 }} />}
                        {Math.round((entry.total_score ?? 0) * 100)}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <Text style={{ fontSize: 13, fontWeight: isRead ? 400 : 500, color: isRead ? '#6b7280' : '#1a1a1a', display: 'block', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {favorited && <StarFilled style={{ color: '#f59e0b', marginRight: 4 }} />}
                          {likeState === 1 && <span>👍</span>}
                          {likeState === -1 && <span>👎</span>}
                          {entry.title}
                        </Text>
                        <div style={{ fontSize: 11, color: '#6b7280', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span>{entry.feed_name || ''}</span>
                          <span>·</span>
                          <span>{formatDate(entry.published_at)}</span>
                          {!isRead && <Badge count="●" style={{ background: '#3b82f6', fontSize: 8, minWidth: 8, height: 8 }} />}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })
            ) : (
              <Empty description={t('dashboard.noArticles')} style={{ marginTop: 40 }} />
            )}
          </div>
        </div>
      </Sider>

      {/* Right panel: entry content */}
      <Content style={{ background: '#fff', display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
        {selectedEntry ? (
          <>
            <div style={{ padding: 20, borderBottom: '1px solid #e5e7eb', flexShrink: 0 }}>
              <Title level={4} style={{ marginBottom: 8 }}>{selectedEntry.title}</Title>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#6b7280', flexWrap: 'wrap' }}>
                <Text type="secondary">{(entryContent as any)?.feed_name || selectedEntry.feed_name || ''}</Text>
                <span>·</span>
                <Text type="secondary">{formatDate(selectedEntry.published_at)}</Text>
                {(entryContent as any)?.word_count && (
                  <><span>·</span><Text type="secondary">{(entryContent as any)?.word_count} {t('article.words')}</Text></>
                )}
                <span>·</span>
                <a href={selectedEntry.url} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', fontSize: 12 }}>
                  🔗 {t('article.original')}
                </a>
              </div>
              {selectedEntry.tags && selectedEntry.tags.length > 0 && (
                <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {selectedEntry.tags.map((tag, idx) => (
                    <Tag key={idx} color={tag.category === 'interest' ? 'blue' : tag.category === 'entity' ? 'purple' : 'default'}>
                      {tag.name}
                    </Tag>
                  ))}
                </div>
              )}
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <Button size="small" icon={<LikeOutlined />} type={getLikeState(selectedEntry) === 1 ? 'primary' : 'default'} onClick={() => toggleLike(selectedEntry.id)}>{t('article.like')}</Button>
                <Button size="small" icon={<DislikeOutlined />} type={getLikeState(selectedEntry) === -1 ? 'primary' : 'default'} danger={getLikeState(selectedEntry) === -1} onClick={() => setDislike(selectedEntry.id)}>{t('article.dislike')}</Button>
                <Button size="small" icon={isFavorited(selectedEntry) ? <StarFilled /> : <StarOutlined />} type={isFavorited(selectedEntry) ? 'primary' : 'default'} onClick={() => toggleFavorite(selectedEntry.id)}>{t('article.favorite')}</Button>
                <Button size="small" icon={<TranslationOutlined />} onClick={handleTranslate} loading={isTranslating} disabled={!llmAvailable}>{t('article.translate')}</Button>
                <Button size="small" icon={<RobotOutlined />} onClick={() => {
                  // Send entry IDs (single or multi) to AI for smart content retrieval
                  const ids = selectedEntryIds.size > 0
                    ? Array.from(selectedEntryIds)
                    : [selectedEntry.id]
                  localStorage.setItem('entrofeed_pending_articles', JSON.stringify(ids))
                  navigate('/agent')
                }}>
                  {t('agent.title') || 'AI'}
                </Button>
              </div>
            </div>

            <Modal title={`🌐 ${t('article.translation')}`} open={showTranslation} onCancel={() => setShowTranslation(false)} footer={null} width={700}>
              <div dangerouslySetInnerHTML={{ __html: translatedContent || '' }} style={{ lineHeight: 1.8 }} />
            </Modal>

            <div style={{ flex: 1, overflow: 'auto', padding: 24, lineHeight: 1.8 }}>
              {isLoadingContent ? (
                <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" /></div>
              ) : (
                <div dangerouslySetInnerHTML={{ __html: (entryContent as any)?.content || '' }} />
              )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
            <div style={{ fontSize: 64, marginBottom: 16 }}>📖</div>
            <Text type="secondary">{t('article.selectToRead') || 'Select an article to read'}</Text>
          </div>
        )}
      </Content>
    </AntLayout>
  )
}
