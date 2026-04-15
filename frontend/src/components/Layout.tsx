import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Layout as AntLayout, Menu, Badge, Switch, Typography } from 'antd'
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

const { Sider, Content } = AntLayout
const { Text } = Typography

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
      <Sider width={260} style={{ background: '#fff', borderRight: '1px solid #e5e7eb' }}>
        <div style={{ padding: '20px', borderBottom: '1px solid #e5e7eb' }}>
          <Text strong style={{ fontSize: 18 }}>📖 EntroFeed</Text>
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

        <div style={{ borderTop: '1px solid #e5e7eb', marginTop: 'auto', padding: '12px' }}>
          <Text type="secondary" style={{ fontSize: 11, textTransform: 'uppercase', padding: '8px 12px', display: 'block' }}>
            {t('dashboard.feeds')}
          </Text>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {sortedFeeds.slice(0, 20).map((feed) => {
              const dynamicStats = feedEntryStats[feed.id]
              const isActive = location.pathname === '/reader' && selectedFeedId === feed.id
              const unreadCount = dynamicStats?.unreadCount ?? 0
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
                  <div
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: 6,
                      backgroundColor: '#f3f4f6',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 11,
                      fontWeight: 600,
                    }}
                  >
                    {feed.name.charAt(0).toUpperCase()}
                  </div>
                  <span style={{ flex: 1, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {feed.name}
                  </span>
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
          {feeds && feeds.length > 20 && (
            <Link to="/feeds" style={{ color: '#2563eb', fontSize: 12, padding: '8px 12px', display: 'block' }}>
              + {feeds.length - 20} more
            </Link>
          )}
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