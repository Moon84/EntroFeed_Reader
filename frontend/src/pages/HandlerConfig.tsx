import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getHandlerSchema, updateHandler } from '../api/settings'
import { Card, Form, Input, Switch, Button, Typography, Skeleton, Divider } from 'antd'

const { Title, Text } = Typography

export function HandlerConfig() {
  const { type } = useParams<{ type: string }>()
  const qc = useQueryClient()
  const [form] = Form.useForm()

  const { data: schema, isLoading } = useQuery({
    queryKey: ['handler-schema', type],
    queryFn: () => getHandlerSchema(type!),
    enabled: !!type,
  })

  const update = useMutation({
    mutationFn: (config: string) => updateHandler(type!, config),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['handlers'] }),
  })

  const handleFinish = (values: Record<string, string | boolean>) => {
    update.mutate(JSON.stringify(values))
  }

  if (!type) {
    return (
      <div>
        <Title level={3} style={{ marginBottom: 16 }}>Handler Configuration</Title>
        <Text type="secondary">No handler type specified.</Text>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 640 }}>
      <div style={{ marginBottom: 24 }}>
        <Link to="/settings" style={{ fontSize: 13, color: '#6b7280' }}>← Settings</Link>
        <Title level={4} style={{ marginTop: 8 }}>Configure: {type}</Title>
      </div>

      {isLoading ? (
        <Skeleton active />
      ) : (
        <Card size="small">
          <Form form={form} layout="vertical" onFinish={handleFinish}>
            {typeof schema === 'object' && schema !== null ? (
              Object.entries(schema as Record<string, unknown>).map(([key, val]) => {
                const v = val as any
                if (typeof v === 'boolean') {
                  return (
                    <Form.Item key={key} name={key} valuePropName="checked" initialValue={v}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Switch checked={v} />
                        <Text>{v ? 'Enabled' : 'Disabled'}</Text>
                      </div>
                    </Form.Item>
                  )
                }
                return (
                  <Form.Item key={key} name={key} label={key} initialValue={String(v ?? '')}>
                    {typeof v === 'number' ? (
                      <Input type="number" />
                    ) : (
                      <Input />
                    )}
                  </Form.Item>
                )
              })
            ) : (
              <Text type="secondary">No configuration schema available for this handler.</Text>
            )}

            <Divider />

            <Button type="primary" htmlType="submit" loading={update.isPending}>
              {update.isPending ? 'Saving...' : 'Save Configuration'}
            </Button>
          </Form>
        </Card>
      )}
    </div>
  )
}