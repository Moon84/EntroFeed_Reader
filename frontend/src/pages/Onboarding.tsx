import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useUpdateSettings } from '../hooks/useSettings'
import { useUpdateFeed } from '../hooks/useFeeds'
import { Card, Button, Input, Select, Typography, Steps, List, Divider } from 'antd'

const { Title, Text } = Typography

const PRESET_FEEDS = [
  { name: 'Hacker News', url: 'https://news.ycombinator.com/rss', category: 'technology' },
  { name: 'ArXiv CS.AI', url: 'https://rss.arxiv.org/rss/cs.AI', category: 'technology' },
  { name: 'Nature News', url: 'https://www.nature.com/nature.rss', category: 'science' },
  { name: 'The Verge', url: 'https://www.theverge.com/rss/index.xml', category: 'technology' },
]

export function Onboarding() {
  const navigate = useNavigate()
  const updateSettings = useUpdateSettings()
  const updateFeed = useUpdateFeed()
  const [step] = useState(0)
  const [feedUrl, setFeedUrl] = useState('')
  const [feedName, setFeedName] = useState('')
  const [feedCategory, setFeedCategory] = useState('technology')

  const finishOnboarding = () => {
    updateSettings.mutate(
      { theme: 'forest', refresh_interval: 30, recent_hours: 24, reading_speed: 200, send_notification: false, finished_onboarding: true },
      { onSuccess: () => navigate('/') },
    )
  }

  const addFeed = () => {
    if (!feedUrl) return
    updateFeed.mutate(
      { name: feedName || feedUrl, url: feedUrl, category: feedCategory, refresh_enabled: true },
      { onSuccess: () => { setFeedUrl(''); setFeedName('') } },
    )
  }

  const addPreset = (preset: typeof PRESET_FEEDS[0]) => {
    updateFeed.mutate(
      { name: preset.name, url: preset.url, category: preset.category, refresh_enabled: true },
    )
  }

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', paddingTop: 32 }}>
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <Title level={2} style={{ marginBottom: 8 }}>Welcome to EntroFeed</Title>
        <Text type="secondary">Your intelligent feed reader.</Text>
      </div>

      <Steps
        current={step}
        items={[
          { title: 'Add Feeds' },
          { title: 'Done' },
        ]}
        style={{ marginBottom: 32 }}
      />

      {step === 0 && (
        <Card title="Add your first feed" size="small">
          <List
            size="small"
            dataSource={PRESET_FEEDS}
            renderItem={(preset) => (
              <List.Item
                actions={[
                  <Button key="add" size="small" onClick={() => addPreset(preset)}>Add</Button>
                ]}
              >
                <List.Item.Meta title={preset.name} description={preset.category} />
              </List.Item>
            )}
          />

          <Divider plain style={{ margin: '16px 0' }}>or add custom</Divider>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <Text type="secondary" style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>Feed URL</Text>
              <Input
                type="url"
                value={feedUrl}
                onChange={(e) => setFeedUrl(e.target.value)}
                placeholder="https://example.com/feed.xml"
              />
            </div>

            <div>
              <Text type="secondary" style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>Name (optional)</Text>
              <Input
                type="text"
                value={feedName}
                onChange={(e) => setFeedName(e.target.value)}
                placeholder="My Blog"
              />
            </div>

            <div>
              <Text type="secondary" style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>Category</Text>
              <Select value={feedCategory} onChange={setFeedCategory} style={{ width: '100%' }}>
                <Select.Option value="technology">Technology</Select.Option>
                <Select.Option value="science">Science</Select.Option>
                <Select.Option value="business">Business</Select.Option>
                <Select.Option value="health">Health</Select.Option>
                <Select.Option value="general">General</Select.Option>
              </Select>
            </div>

            <Button type="primary" onClick={addFeed} disabled={!feedUrl} loading={updateFeed.isPending}>
              {updateFeed.isPending ? 'Adding...' : 'Add Feed'}
            </Button>
          </div>
        </Card>
      )}

      {step === 1 && (
        <Card size="small" style={{ textAlign: 'center' }}>
          <div style={{ marginBottom: 16 }}>
            <Title level={4} style={{ marginBottom: 8 }}>You're all set!</Title>
            <Text type="secondary">
              Start reading your feeds and EntroFeed will learn your interests.
            </Text>
          </div>
          <Button type="primary" onClick={finishOnboarding} size="large">
            Go to Dashboard →
          </Button>
        </Card>
      )}

      <div style={{ textAlign: 'center', marginTop: 24 }}>
        <Link to="/" onClick={finishOnboarding} style={{ color: '#6b7280' }}>
          Skip onboarding
        </Link>
      </div>
    </div>
  )
}