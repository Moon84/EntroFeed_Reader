import { useLocation, useNavigate, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Layout as AntLayout, Menu, Badge, Switch, Typography, Tag } from 'antd'
import {
  DashboardOutlined,
  ReadOutlined,
  UnorderedListOutlined,
  ClockCircleOutlined,
  StarOutlined,
  RobotOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useFeeds } from '../hooks/useFeeds'
import { useReader } from '../context/ReaderContext'
import { getLLMStatus } from '../client-api/entries'

const { Sider, Content } = AntLayout
const { Text } = Typography

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

// Helper to get favicon URL from feed URL
function getFaviconUrl(feedUrl: string): string {
  try {
    const url = new URL(feedUrl)
    return `https://www.google.com/s2/favicons?domain=${url.hostname}&sz=32`
  } catch {
    return ''
  }
}

const NAV_ITEMS = [
  { path: '/', labelKey: 'nav.dashboard', icon: <DashboardOutlined /> },
  { path: '/reader', labelKey: 'nav.reader', icon: <ReadOutlined /> },
  { path: '/feeds', labelKey: 'nav.feeds', icon: <UnorderedListOutlined /> },
  { path: '/recent', labelKey: 'nav.recent', icon: <ClockCircleOutlined /> },
  { path: '/recommendations', labelKey: 'nav.recommendations', icon: <StarOutlined /> },
  { path: '/agent', labelKey: 'nav.agent', icon: <RobotOutlined /> },
  { path: '/settings', labelKey: 'nav.settings', icon: <SettingOutlined /> },
]

export function Layout() {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const { data: feeds } = useFeeds()
  const { selectedFeedId, setSelectedFeedId, feedEntryStats } = useReader()
  const { data: llmStatus } = useQuery<LLMStatus>({
    queryKey: ['llm-status'],
    queryFn: getLLMStatus,
    refetchInterval: 60000, // Refresh every minute
  })

  const toggleLanguage = () => {
    const newLang = i18n.language === 'zh' ? 'en' : 'zh'
    i18n.changeLanguage(newLang)
    localStorage.setItem('language', newLang)
  }

  const handleFeedClick = (feedId: string) => {
    if (location.pathname !== '/reader') {
      navigate('/reader')
    }
    setSelectedFeedId(selectedFeedId === feedId ? null : feedId)
  }

  const selectedKey = NAV_ITEMS.find((item) =>
    item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path)
  )?.path || '/'

  // Sort feeds by important count
  const sortedFeeds = [...(feeds || [])].sort((a, b) => {
    const statsA = feedEntryStats[a.id]
    const statsB = feedEntryStats[b.id]
    const importantA = statsA?.importantCount ?? 0
    const importantB = statsB?.importantCount ?? 0
    return importantB - importantA
  })

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider width={260} style={{ background: '#fff', borderRight: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <img
              src="/assets/EntroFeed_logo.png"
              alt="EntroFeed"
              style={{ height: 32 }}
            />
            <Text strong style={{ fontSize: 16 }}>{i18n.language === 'zh' ? '熵流' : 'EntroFeed'}</Text>
          </div>
          {llmStatus && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Tag color={llmStatus.available ? 'green' : 'red'} style={{ margin: 0, fontSize: 11 }}>
                {llmStatus.available ? `${llmStatus.provider}` : 'LLM Offline'}
              </Tag>
              {llmStatus.available && llmStatus.usage && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  📊 {llmStatus.usage.total_tokens.toLocaleString()} tokens
                </Text>
              )}
            </div>
          )}
        </div>

        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          style={{ border: 'none', padding: '12px 0' }}
          items={NAV_ITEMS.map((item) => ({
            key: item.path,
            icon: item.icon,
            label: t(item.labelKey),
            onClick: () => navigate(item.path),
          }))}
        />

        <div style={{ borderTop: '1px solid #e5e7eb', padding: '12px' }}>
          <Text type="secondary" style={{ fontSize: 11, textTransform: 'uppercase', padding: '8px 12px', display: 'block' }}>
            {t('dashboard.feeds')}
          </Text>
          <div style={{ maxHeight: 240, overflowY: 'auto' }}>
            {sortedFeeds.slice(0, 20).map((feed) => {
              const dynamicStats = feedEntryStats[feed.id]
              const isActive = location.pathname === '/reader' && selectedFeedId === feed.id
              const unreadCount = dynamicStats?.unreadCount ?? 0
              const importantCount = dynamicStats?.importantCount ?? 0
              const hasStats = dynamicStats && dynamicStats.totalCount > 0

              return (
                <div
                  key={feed.id}
                  onClick={() => handleFeedClick(feed.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 12px',
                    borderRadius: 8,
                    cursor: 'pointer',
                    background: isActive ? '#eff6ff' : 'transparent',
                    color: isActive ? '#2563eb' : '#666',
                  }}
                >
                  <img
                    src={getFaviconUrl(feed.url)}
                    alt=""
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: 4,
                      objectFit: 'contain',
                    }}
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none'
                      ;(e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden')
                    }}
                  />
                  <span
                    className="feed-letter"
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: 4,
                      backgroundColor: '#f3f4f6',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 10,
                      fontWeight: 600,
                      flexShrink: 0,
                    }}
                  >
                    {feed.name.charAt(0).toUpperCase()}
                  </span>
                  <span style={{ flex: 1, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {feed.name}
                  </span>
                  {hasStats && importantCount > 0 && (
                    <Badge
                      count={importantCount}
                      size="small"
                      style={{ backgroundColor: '#f59e0b' }}
                    />
                  )}
                  {hasStats && (
                    <Badge
                      count={unreadCount}
                      size="small"
                      style={{ backgroundColor: '#3b82f6' }}
                    />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        <div style={{ padding: 12, borderTop: '1px solid #e5e7eb' }}>
          <Switch
            checkedChildren="中"
            unCheckedChildren="EN"
            checked={i18n.language === 'zh'}
            onChange={toggleLanguage}
            size="small"
          />
        </div>
      </Sider>

      <AntLayout>
        <Content style={{ padding: '24px 32px', background: '#f7f8fa', overflow: 'auto' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}