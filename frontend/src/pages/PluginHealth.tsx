import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, Typography, Tag, Badge, Spin, Empty, Table, Modal, Form, Input, Button, Divider, message } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
  SettingOutlined,
} from '@ant-design/icons'

const { Title, Text } = Typography

interface PluginCheckResult {
  available: boolean
  reason: string | null
  missing_env: string[]
}

interface PluginHealthResponse {
  plugins: Record<string, Record<string, PluginCheckResult>>
  summary: Record<string, { total: number; available: number }>
}

interface PluginRow {
  key: string
  id: string
  type: string
  available: boolean
  reason: string | null
  missing_env: string[]
}

function getStatusTag(available: boolean, missingEnv: string[], reason: string | null) {
  if (available) {
    return <Tag color="success">Healthy</Tag>
  }
  if (missingEnv && missingEnv.length > 0) {
    return <Tag color="warning">Not configured</Tag>
  }
  if (reason && String(reason).includes('No availability check')) {
    return <Tag color="default">Unknown</Tag>
  }
  return <Tag color="error">Offline</Tag>
}

function getRowIcon(available: boolean, missingEnv: string[], reason: string | null) {
  if (available) {
    return <CheckCircleOutlined style={{ color: '#22c55e' }} />
  }
  if (missingEnv && missingEnv.length > 0) {
    return <ExclamationCircleOutlined style={{ color: '#eab308' }} />
  }
  if (reason && String(reason).includes('No availability check')) {
    return <ExclamationCircleOutlined style={{ color: '#6b7280' }} />
  }
  return <CloseCircleOutlined style={{ color: '#ef4444' }} />
}

// Inline config form component
function HandlerConfigForm({ handlerId, onClose }: { handlerId: string; onClose: () => void }) {
  const [form] = Form.useForm()
  const qc = useQueryClient()

  const { data: schemaData, isLoading: isLoadingSchema } = useQuery({
    queryKey: ['handler-schema', handlerId],
    queryFn: async () => {
      const res = await fetch(`/settings/${handlerId}`)
      if (!res.ok) throw new Error('Failed to fetch schema')
      return res.json()
    },
  })

  const { data: configData, isLoading: isLoadingConfig } = useQuery({
    queryKey: ['handler-config', handlerId],
    queryFn: async () => {
      const res = await fetch(`/settings/${handlerId}`)
      if (!res.ok) throw new Error('Failed to fetch config')
      return res.json()
    },
  })

  const saveMutation = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      const res = await fetch('/api/update_handler/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          handler: handlerId,
          config: JSON.stringify(values),
        }),
      })
      if (!res.ok) throw new Error('Failed to save')
    },
    onSuccess: () => {
      message.success('Configuration saved')
      qc.invalidateQueries({ queryKey: ['plugin-health'] })
      qc.invalidateQueries({ queryKey: ['handler-config', handlerId] })
      onClose()
    },
    onError: () => {
      message.error('Failed to save configuration')
    },
  })

  const rawSchema = schemaData?.schema
  const schema = (() => {
    try {
      return typeof rawSchema === 'string' ? JSON.parse(rawSchema) : rawSchema
    } catch {
      return {}
    }
  })()
  const rawConfig = configData?.handler?.config
  const initialValues = (() => {
    try {
      return rawConfig ? JSON.parse(rawConfig) : {}
    } catch {
      return {}
    }
  })()

  return (
    <div>
      {isLoadingSchema || isLoadingConfig ? (
        <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
      ) : (
        <Form
          form={form}
          layout="vertical"
          initialValues={initialValues}
          onFinish={saveMutation.mutate}
        >
          {schema && typeof schema === 'object'
            ? Object.entries(schema as Record<string, unknown>).map(([key, val]) => {
              const v = val as any
              return (
                <Form.Item
                  key={key}
                  name={key}
                  label={v?.description || key}
                  extra={v?.default !== undefined ? `Default: ${v.default}` : undefined}
                >
                  {v?.type === 'number' ? (
                    <Input type="number" />
                  ) : v?.type === 'boolean' ? (
                    <Input type="checkbox" />
                  ) : (
                    <Input />
                  )}
                </Form.Item>
              )
            })
            : (
              <Text type="secondary">No configuration schema available.</Text>
            )}

          <Divider />

          <div style={{ display: 'flex', gap: 8 }}>
            <Button type="primary" htmlType="submit" loading={saveMutation.isPending}>
              Save
            </Button>
            <Button onClick={onClose}>Cancel</Button>
          </div>
        </Form>
      )}
    </div>
  )
}

export function PluginHealth() {
  const { data, isLoading, error, refetch } = useQuery<PluginHealthResponse>({
    queryKey: ['plugin-health'],
    queryFn: async () => {
      const res = await fetch('/api/plugins/health')
      if (!res.ok) throw new Error('Failed to fetch plugin health')
      return res.json()
    },
    refetchInterval: 30000,
  })

  const [configTarget, setConfigTarget] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">Loading plugin status...</Text>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <Title level={3}>Plugin Health</Title>
          <Badge status="error" text="Failed to load" />
        </div>
        <Empty description="Failed to fetch plugin health data" />
      </div>
    )
  }

  const pluginTypes = Object.keys(data.plugins)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>Plugin Health</Title>
        <a onClick={() => refetch()} style={{ cursor: 'pointer' }}>
          <SyncOutlined spin={isLoading} /> Refresh
        </a>
      </div>

      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        {pluginTypes.map((type) => {
          const summary = data.summary[type]
          const allAvailable = summary.total === summary.available
          const hasWarnings = summary.available > 0 && !allAvailable
          return (
            <Card
              key={type}
              size="small"
              style={{
                borderColor: allAvailable ? '#22c55e' : hasWarnings ? '#eab308' : '#ef4444',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <Text strong style={{ textTransform: 'capitalize', fontSize: 14 }}>
                    {type}
                  </Text>
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {summary.available} / {summary.total} available
                    </Text>
                  </div>
                </div>
                <Badge
                  status={allAvailable ? 'success' : hasWarnings ? 'warning' : 'error'}
                  text=""
                />
              </div>
            </Card>
          )
        })}
      </div>

      {/* Plugin Details by Category */}
      {pluginTypes.map((type) => {
        const plugins = data.plugins[type]
        const pluginList = Object.entries(plugins)

        const columns = [
          {
            title: 'Plugin',
            dataIndex: 'id',
            key: 'id',
            render: (id: string, record: PluginRow) => (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {getRowIcon(record.available, record.missing_env, record.reason)}
                <Text strong style={{ fontFamily: 'monospace' }}>
                  {id}
                </Text>
              </div>
            ),
          },
          {
            title: 'Status',
            dataIndex: 'available',
            key: 'status',
            width: 130,
            render: (available: boolean, record: PluginRow) => getStatusTag(available, record.missing_env, record.reason),
          },
          {
            title: 'Reason',
            dataIndex: 'reason',
            key: 'reason',
            render: (reason: string | null) => (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {reason || '-'}
              </Text>
            ),
          },
          {
            title: 'Missing Env',
            dataIndex: 'missing_env',
            key: 'missing_env',
            width: 200,
            render: (missingEnv: string[]) => (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {missingEnv && missingEnv.length > 0 ? (
                  missingEnv.map((env) => (
                    <Tag key={env} color="orange" style={{ fontSize: 11 }}>
                      {env}
                    </Tag>
                  ))
                ) : (
                  <Text type="secondary">-</Text>
                )}
              </div>
            ),
          },
          {
            title: '',
            key: 'action',
            width: 80,
            render: (_: unknown, record: PluginRow) => {
              if (record.available) return null
              return (
                <Button
                  size="small"
                  icon={<SettingOutlined />}
                  onClick={() => setConfigTarget(record.id)}
                >
                  Config
                </Button>
              )
            },
          },
        ]

        const tableData = pluginList.map(([id, info]) => ({
          key: id,
          id,
          type,
          ...info,
        }))

        return (
          <Card
            key={type}
            size="small"
            title={
              <span style={{ textTransform: 'capitalize' }}>
                {type} Plugins
              </span>
            }
            style={{ marginBottom: 16 }}
          >
            <Table
              columns={columns}
              dataSource={tableData}
              pagination={false}
              size="small"
            />
          </Card>
        )
      })}

      {pluginTypes.length === 0 && (
        <Empty description="No plugins registered" />
      )}

      {/* Config Modal */}
      <Modal
        title={`Configure: ${configTarget}`}
        open={!!configTarget}
        onCancel={() => setConfigTarget(null)}
        footer={null}
        width={500}
      >
        {configTarget && (
          <HandlerConfigForm
            handlerId={configTarget}
            onClose={() => setConfigTarget(null)}
          />
        )}
      </Modal>
    </div>
  )
}
