import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useFeeds, useUpdateFeed } from '../hooks/useFeeds'
import { Card, Form, Input, Switch, Button, Select, Typography, Divider } from 'antd'

const { Title, Text } = Typography

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

  const handleFinish = (values: FormState) => {
    updateFeed.mutate(
      { ...values, notify_destination: values.notify_destination || undefined },
      { onSuccess: () => navigate('/feeds') },
    )
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

          <Form.Item name="url" label="URL" rules={[{ required: true, type: 'url' }]}>
            <Input placeholder="https://example.com/feed.xml" />
          </Form.Item>

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