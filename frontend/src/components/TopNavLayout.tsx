import { useLocation, useNavigate, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Layout as AntLayout, Menu, Typography } from 'antd'
import {
  DashboardOutlined,
  ReadOutlined,
  UnorderedListOutlined,
  ClockCircleOutlined,
  RobotOutlined,
  SettingOutlined,
  AppstoreOutlined,
} from '@ant-design/icons'
import { getLLMStatus } from '../client-api/entries'

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

type LLMHealthStatus = 'healthy' | 'degraded' | 'offline' | 'unknown'

function getLLMHealthStatus(llmStatus: LLMStatus | undefined): LLMHealthStatus {
  if (!llmStatus) return 'unknown'
  if (!llmStatus.available) return 'offline'
  if (llmStatus.error) return 'degraded'
  if (llmStatus.usage && llmStatus.usage.limit > 0) {
    const usagePercent = (llmStatus.usage.total_tokens / llmStatus.usage.limit) * 100
    if (usagePercent > 80) return 'degraded'
  }
  return 'healthy'
}

function getLLMStatusColor(status: LLMHealthStatus): { bg: string; border: string; text: string; dot: string } {
  switch (status) {
    case 'healthy':
      return { bg: '#f0fdf4', border: '#22c55e', text: '#166534', dot: '#22c55e' }
    case 'degraded':
      return { bg: '#fefce8', border: '#eab308', text: '#854d0e', dot: '#eab308' }
    case 'offline':
      return { bg: '#fef2f2', border: '#ef4444', text: '#991b1b', dot: '#ef4444' }
    default:
      return { bg: '#f9fafb', border: '#d1d5db', text: '#6b7280', dot: '#9ca3af' }
  }
}

const NAV_ITEMS = [
  { path: '/', labelKey: 'nav.dashboard', icon: <DashboardOutlined /> },
  { path: '/reader', labelKey: 'nav.reader', icon: <ReadOutlined /> },
  { path: '/feeds', labelKey: 'nav.feeds', icon: <UnorderedListOutlined /> },
  { path: '/recent', labelKey: 'nav.recent', icon: <ClockCircleOutlined /> },
  { path: '/agent', labelKey: 'nav.agent', icon: <RobotOutlined /> },
  { path: '/plugins', labelKey: 'nav.plugins', icon: <AppstoreOutlined /> },
  { path: '/settings', labelKey: 'nav.settings', icon: <SettingOutlined /> },
]

export function TopNavLayout() {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const { data: llmStatus } = useQuery<LLMStatus>({
    queryKey: ['llm-status'],
    queryFn: getLLMStatus,
    refetchInterval: 60000,
  })

  const toggleLanguage = () => {
    const newLang = i18n.language === 'zh' ? 'en' : 'zh'
    i18n.changeLanguage(newLang)
    localStorage.setItem('language', newLang)
  }

  const selectedKey = NAV_ITEMS.find((item) =>
    item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path)
  )?.path || '/'

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <AntLayout.Header
        style={{
          background: '#fff',
          borderBottom: '1px solid #e5e7eb',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          gap: 24,
          height: 56,
          lineHeight: '56px',
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
      >
        {/* Logo + brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <img src="/assets/EntroFeed_logo.png" alt="EntroFeed" style={{ height: 28 }} />
          <Text strong style={{ fontSize: 15 }}>{i18n.language === 'zh' ? '熵流' : 'EntroFeed'}</Text>
        </div>

        {/* Horizontal nav */}
        <Menu
          mode="horizontal"
          selectedKeys={[selectedKey]}
          style={{ border: 'none', flex: 1, minWidth: 0 }}
          items={NAV_ITEMS.map((item) => ({
            key: item.path,
            icon: item.icon,
            label: t(item.labelKey),
            onClick: () => navigate(item.path),
          }))}
        />

        {/* Right side: LLM status + language switch */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          {llmStatus && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 6,
                border: `1px solid ${getLLMStatusColor(getLLMHealthStatus(llmStatus)).border}`,
                backgroundColor: getLLMStatusColor(getLLMHealthStatus(llmStatus)).bg,
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  backgroundColor: getLLMStatusColor(getLLMHealthStatus(llmStatus)).dot,
                  flexShrink: 0,
                }}
              />
              <Text style={{ fontSize: 11, color: getLLMStatusColor(getLLMHealthStatus(llmStatus)).text }}>
                {llmStatus.available ? `${llmStatus.provider}/${llmStatus.model}` : 'LLM Offline'}
              </Text>
            </div>
          )}

          <button
            onClick={toggleLanguage}
            style={{
              border: '1px solid #d9d9d9',
              borderRadius: 4,
              padding: '2px 8px',
              background: '#fff',
              cursor: 'pointer',
              fontSize: 12,
              fontWeight: 500,
            }}
          >
            {i18n.language === 'zh' ? 'EN' : '中'}
          </button>
        </div>
      </AntLayout.Header>

      <AntLayout.Content style={{
          background: '#f7f8fa',
          height: 'calc(100vh - 56px)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
        <div style={{ flex: 1, overflow: 'auto', padding: '24px 32px' }}>
          <Outlet />
        </div>
      </AntLayout.Content>
    </AntLayout>
  )
}
