import { useQuery } from '@tanstack/react-query'
import { getAbout } from '../client-api/settings'
import { useBackup } from '../hooks/useSettings'
import { Link } from 'react-router-dom'
import { Card, Typography, Button, List, Skeleton } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

export function About() {
  const { data: info, isLoading } = useQuery({
    queryKey: ['about'],
    queryFn: getAbout,
  })
  const backup = useBackup()

  const handleBackup = () => {
    backup.mutateAsync().then((blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `entrofeed-backup-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    })
  }

  return (
    <div style={{ maxWidth: 640 }}>
      <Title level={3} style={{ marginBottom: 24 }}>About EntroFeed</Title>

      {isLoading ? (
        <Skeleton active />
      ) : info ? (
        <Card size="small" title="EntroFeed" style={{ marginBottom: 16 }}>
          <List size="small">
            <List.Item><Text type="secondary">Version:</Text> <Text>{info.version}</Text></List.Item>
            <List.Item><Text type="secondary">Python:</Text> <Text>{info.python_version}</Text></List.Item>
            <List.Item><Text type="secondary">FastAPI:</Text> <Text>{info.fastapi_version}</Text></List.Item>
            <List.Item><Text type="secondary">Storage:</Text> <Text>{info.storage_handler}</Text></List.Item>
            <List.Item><Text type="secondary">Docker:</Text> <Text>{info.docker ? 'Yes' : 'No'}</Text></List.Item>
            <List.Item>
              <Text type="secondary">GitHub:</Text>
              <a href={info.github} target="_blank" rel="noopener" style={{ marginLeft: 8 }}>{info.github}</a>
            </List.Item>
          </List>
        </Card>
      ) : null}

      <Card size="small" title="Backup & Restore" style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          Download a backup of your feeds, settings, and interests.
        </Text>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button icon={<DownloadOutlined />} onClick={handleBackup} loading={backup.isPending}>
            {backup.isPending ? 'Creating...' : 'Download Backup'}
          </Button>
          <Link to="/settings">
            <Button>Restore from Backup</Button>
          </Link>
        </div>
      </Card>

      <Card size="small" title="Features">
        <List size="small">
          <List.Item>BM25-based priority scoring with synonym expansion</List.Item>
          <List.Item>Authority scoring from trusted source registry</List.Item>
          <List.Item>Recency-weighted relevance for fresh content</List.Item>
          <List.Item>Ontology-based interest matching</List.Item>
          <List.Item>Full-text content retrieval with reading metrics</List.Item>
          <List.Item>OPML import/export for feed portability</List.Item>
        </List>
      </Card>
    </div>
  )
}