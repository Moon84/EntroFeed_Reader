import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useFeeds, useUpdateFeed } from '../hooks/useFeeds'
import { Card, Form, Input, Switch, Button, Select, Typography, Divider, List, Tag, message } from 'antd'
import { discoverRSSHub, type RSSHubRoute } from '../client-api/feeds'

const { Title, Text } = Typography

// RSSHub protocol helper
const RSSHUB_HOST = import.meta.env.VITE_RSSHUB_HOST || 'http://localhost:1200'

function parseRsshubUrl(url: string): { route: string; fullUrl: string; name: string } | null {
  if (!url.startsWith('rsshub://')) return null
  const route = url.slice('rsshub://'.length)
  const parts = route.split('/')
  const name = parts.length >= 3
    ? `${parts[0].charAt(0).toUpperCase() + parts[0].slice(1)} ${parts[2]}`
    : route
  return {
    route,
    fullUrl: `${RSSHUB_HOST}/${route}`,
    name,
  }
}

interface FormState {
  name: string
  url: string
  category: string
  notify_destination: string
  notify: boolean
  preview_only: boolean
  refresh_enabled: boolean
  use_script: boolean
  retrieve_content: boolean
}

const EMPTY: FormState = {
  name: '',
  url: '',
  category: 'general',
  notify_destination: '',
  notify: false,
  preview_only: false,
  refresh_enabled: true,
  use_script: false,
  retrieve_content: false,
}

export function FeedEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: feeds } = useFeeds()
  const updateFeed = useUpdateFeed()
  const [form] = Form.useForm()

  const existing = id && id !== 'new' ? feeds?.find((f) => f.id === id) : null
  const isNew = !existing

  const [formData, setFormData] = useState<FormState>(EMPTY)
  const [discoveredRoutes, setDiscoveredRoutes] = useState<RSSHubRoute[]>([])

  useEffect(() => {
    if (existing) {
      setFormData({
        name: existing.name,
        url: existing.url,
        category: existing.category,
        notify_destination: existing.notify_destination ?? '',
        notify: existing.notify,
        preview_only: existing.preview_only,
        refresh_enabled: existing.refresh_enabled,
        use_script: existing.use_script ?? false,
        retrieve_content: existing.retrieve_content ?? false,
      })
      form.setFieldsValue({
        name: existing.name,
        url: existing.url,
        category: existing.category,
        notify_destination: existing.notify_destination ?? '',
        notify: existing.notify,
        preview_only: existing.preview_only,
        refresh_enabled: existing.refresh_enabled,
        use_script: existing.use_script ?? false,
        retrieve_content: existing.retrieve_content ?? false,
      })
    }
  }, [existing, form])

  const discoverRoutes = useCallback(async (url: string) => {
    // Skip if already a rsshub:// URL
    if (url.startsWith('rsshub://') || !url.startsWith('http')) {
      setDiscoveredRoutes([])
      return
    }

    // discovering...
    try {
      const routes = await discoverRSSHub(url)
      setDiscoveredRoutes(routes)
    } catch (err) {
      console.error('Failed to discover routes:', err)
      setDiscoveredRoutes([])
    } finally {
      // done
    }
  }, [])

  const handleFinish = (values: FormState) => {
    // Transform rsshub:// URLs to full RSSHub URLs
    const rsshubInfo = parseRsshubUrl(values.url)
    const finalValues = rsshubInfo
      ? { ...values, url: rsshubInfo.fullUrl, name: values.name || rsshubInfo.name }
      : values

    updateFeed.mutate(
      { ...finalValues, notify_destination: values.notify_destination || undefined },
      { onSuccess: () => navigate('/feeds') },
    )
  }

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const url = e.target.value
    const rsshubInfo = parseRsshubUrl(url)
    if (rsshubInfo && !formData.name) {
      form.setFieldsValue({ name: rsshubInfo.name })
      setFormData(prev => ({ ...prev, name: rsshubInfo.name }))
    }
    // Trigger RSSHub route discovery for regular URLs
    if (url.length > 10) {
      discoverRoutes(url)
    } else {
      setDiscoveredRoutes([])
    }
  }

  const selectDiscoveredRoute = (route: RSSHubRoute) => {
    form.setFieldsValue({
      url: route.url,
      name: route.title,
    })
    setFormData(prev => ({ ...prev, url: route.url, name: route.title }))
    setDiscoveredRoutes([])
    message.success(`Selected: ${route.title}`)
  }

  return (
    <div style={{ maxWidth: 640 }}>
      <div style={{ marginBottom: 24 }}>
        <Link to="/feeds" style={{ fontSize: 13, color: '#6b7280' }}>← Feeds</Link>
        <Title level={4} style={{ marginTop: 8 }}>{isNew ? 'Add Feed' : 'Edit Feed'}</Title>
      </div>

      <Card size="small">
        <Form form={form} layout="vertical" onFinish={handleFinish} initialValues={formData}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="My Feed" />
          </Form.Item>

          <Form.Item
            name="url"
            label="URL"
            rules={[{ required: true }]}
            extra={!isNew ? undefined : (
              <span style={{ fontSize: 12, color: '#6b7280' }}>
                Supports rsshub:// protocol, e.g. rsshub://twitter/user/elonmusk
              </span>
            )}
          >
            <Input
              placeholder="https://example.com/feed.xml or rsshub://twitter/user/elonmusk"
              onChange={handleUrlChange}
            />
          </Form.Item>

          {/* RSSHub Route Discovery Results */}
          {discoveredRoutes.length > 0 && (
            <div style={{ marginBottom: 16, padding: 12, background: '#f0f9ff', borderRadius: 8, border: '1px solid #e0f2fe' }}>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
                RSSHub routes discovered:
              </Text>
              <List
                size="small"
                dataSource={discoveredRoutes}
                renderItem={(route) => (
                  <List.Item style={{ padding: '8px 0' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
                      <Tag color="blue">{route.title}</Tag>
                      <code style={{ flex: 1, fontSize: 11 }}>{route.url}</code>
                      <Button size="small" onClick={() => selectDiscoveredRoute(route)}>
                        Use
                      </Button>
                    </div>
                  </List.Item>
                )}
              />
            </div>
          )}

          <Form.Item name="category" label="Category">
            <Select>
              <Select.Option value="general">General</Select.Option>
              <Select.Option value="technology">Technology</Select.Option>
              <Select.Option value="science">Science</Select.Option>
              <Select.Option value="business">Business</Select.Option>
              <Select.Option value="health">Health</Select.Option>
              <Select.Option value="entertainment">Entertainment</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="notify_destination" label="Notify Destination (optional)">
            <Input placeholder="email, slack webhook, etc." />
          </Form.Item>

          <Divider />

          <Form.Item name="refresh_enabled" valuePropName="checked" style={{ marginBottom: 12 }}>
            <Switch checkedChildren="ON" unCheckedChildren="OFF" />
            <Text style={{ marginLeft: 8 }}>Auto-refresh enabled</Text>
          </Form.Item>

          <Form.Item name="notify" valuePropName="checked" style={{ marginBottom: 12 }}>
            <Switch checkedChildren="ON" unCheckedChildren="OFF" />
            <Text style={{ marginLeft: 8 }}>Send notifications</Text>
          </Form.Item>

          <Form.Item name="preview_only" valuePropName="checked" style={{ marginBottom: 12 }}>
            <Switch checkedChildren="ON" unCheckedChildren="OFF" />
            <Text style={{ marginLeft: 8 }}>Preview only (no full content)</Text>
          </Form.Item>

          <Form.Item name="use_script" valuePropName="checked" style={{ marginBottom: 12 }}>
            <Switch checkedChildren="ON" unCheckedChildren="OFF" />
            <Text style={{ marginLeft: 8 }}>Use custom script</Text>
          </Form.Item>

          <Form.Item name="retrieve_content" valuePropName="checked" style={{ marginBottom: 24 }}>
            <Switch checkedChildren="ON" unCheckedChildren="OFF" />
            <Text style={{ marginLeft: 8 }}>Retrieve full content</Text>
          </Form.Item>

          <Button type="primary" htmlType="submit" loading={updateFeed.isPending}>
            {updateFeed.isPending ? '...' : isNew ? 'Add Feed' : 'Save Changes'}
          </Button>
        </Form>
      </Card>
    </div>
  )
}
