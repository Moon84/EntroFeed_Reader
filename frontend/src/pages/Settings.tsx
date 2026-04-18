import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useSettings, useUpdateSettings, useBackup, useRestore } from '../hooks/useSettings'
import { useUserProfile, useSaveUserProfile } from '../hooks/useUserProfile'
import { useQuery } from '@tanstack/react-query'
import { getHandlers } from '../client-api/settings'
import { getLLMStatus } from '../client-api/entries'
import { getLLMProviders, getCapabilityLabel, type LLMProvider } from '../client-api/llm'
import { useUIStore } from '../stores/uiStore'
import type { GlobalSettings } from '../types'
import { Card, Form, Input, Select, Button, Typography, Skeleton, Divider, Alert, Space, Tag, Descriptions, Badge } from 'antd'

const { Title, Text } = Typography

export function Settings() {
  const { t } = useTranslation()
  const { data: settings, isLoading } = useSettings()
  const updateSettings = useUpdateSettings()
  const backup = useBackup()
  const restore = useRestore()
  const { data: userProfile } = useUserProfile()
  const saveUserProfile = useSaveUserProfile()
  const { data: handlers } = useQuery({
    queryKey: ['handlers'],
    queryFn: getHandlers,
  })
  const { data: llmStatus } = useQuery({
    queryKey: ['llm-status'],
    queryFn: getLLMStatus,
  })
  const { data: llmProvidersData } = useQuery({
    queryKey: ['llm-providers'],
    queryFn: getLLMProviders,
  })
  const { setTheme } = useUIStore()
  const fileRef = useRef<HTMLInputElement>(null)
  const [form] = Form.useForm()
  const [profileContent, setProfileContent] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)

  const [formData, setFormData] = useState<Partial<GlobalSettings>>({})
  const [effectiveLlM, setEffectiveLlM] = useState<string>('')
  const [selectedProvider, setSelectedProvider] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')

  const llmProviders: LLMProvider[] = llmProvidersData?.providers ?? []
  const currentProvider = llmProviders.find(p => p.id === selectedProvider)
  const currentModel = currentProvider?.models.find(m => m.name === selectedModel)

  useEffect(() => {
    if (settings) {
      const effective = settings.llm_handler_key === 'null_llm'
        ? (llmStatus?.provider || 'null_llm')
        : settings.llm_handler_key
      setEffectiveLlM(effective)
      
      // Try to find the provider from the effective LLM key
      const provider = llmProviders.find(p => p.id === effective)
      if (provider) {
        setSelectedProvider(effective)
        // Try to set the model from llmStatus
        if (llmStatus?.model) {
          const model = provider.models.find(m => m.name === llmStatus.model)
          if (model) {
            setSelectedModel(model.name)
          }
        }
      }
      
      const formValues = { ...settings, llm_handler_key: effective }
      setFormData(formValues)
      setTheme(settings.theme as any)
      form.setFieldsValue(formValues)
    }
  }, [settings, form, llmStatus, llmProviders])

  useEffect(() => {
    if (userProfile?.content) {
      setProfileContent(userProfile.content)
    }
  }, [userProfile])

  const handleSaveProfile = async () => {
    try {
      await saveUserProfile.mutateAsync(profileContent)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (e) {
      console.error('Failed to save profile:', e)
    }
  }

  const handleProviderChange = (providerId: string) => {
    setSelectedProvider(providerId)
    const provider = llmProviders.find(p => p.id === providerId)
    if (provider && provider.models.length > 0) {
      setSelectedModel(provider.models[0].name)
    }
  }

  const handleModelChange = (modelName: string) => {
    setSelectedModel(modelName)
  }

  const handleFinish = (values: Partial<GlobalSettings>) => {
    const wasShowingEffective = settings?.llm_handler_key === 'null_llm'
    const selectedLlM = values.llm_handler_key
    const actualLlM = wasShowingEffective
      ? (selectedLlM === effectiveLlM ? 'null_llm' : selectedLlM)
      : selectedLlM

    updateSettings.mutate({
      theme: values.theme ?? 'forest',
      refresh_interval: values.refresh_interval ?? 30,
      recent_hours: values.recent_hours ?? 24,
      reading_speed: values.reading_speed ?? 200,
      send_notification: values.send_notification ?? false,
      llm: actualLlM,
    })
  }

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

  const handleRestore = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) restore.mutate(file)
  }

  const contentHandlers = handlers?.filter((h) => h.type === 'content') ?? []

  if (isLoading) {
    return (
      <div>
        <Skeleton active paragraph={{ rows: 6 }} />
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 800 }}>
      <Title level={3} style={{ marginBottom: 24 }}>{t('settings.title')}</Title>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginBottom: 16 }}>{t('settings.general')}</Title>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleFinish}
          initialValues={formData}
        >
          <Form.Item label={t('settings.readingSpeed')} name="reading_speed">
            <Input type="number" min={100} max={1000} style={{ width: 120 }} />
          </Form.Item>

          <Form.Item label={t('settings.refreshInterval')} name="refresh_interval">
            <Input type="number" min={5} max={1440} style={{ width: 120 }} suffix="min" />
          </Form.Item>

          <Form.Item label="Recent Hours" name="recent_hours">
            <Input type="number" min={1} max={168} style={{ width: 120 }} suffix="hours" />
          </Form.Item>

          <Divider />

          <Title level={5} style={{ marginBottom: 16 }}>{t('settings.theme')}</Title>

          <Form.Item label="Content" name="content_retrieval_handler_key">
            <Select style={{ width: 200 }} placeholder="Default">
              {contentHandlers.map((h) => (
                <Select.Option key={h.name} value={h.name}>{h.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item style={{ marginTop: 16 }}>
            <Button type="primary" htmlType="submit" loading={updateSettings.isPending}>
              {updateSettings.isPending ? '...' : t('common.save')}
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* LLM Provider Selection */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginBottom: 16 }}>LLM Provider & Model</Title>
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          Select an LLM provider and model for AI-powered features like summaries and recommendations.
        </Text>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleFinish}
          initialValues={formData}
        >
          {/* Provider Selection */}
          <Form.Item label="Provider" required>
            <Select
              style={{ width: 250 }}
              placeholder="Select a provider"
              value={selectedProvider || undefined}
              onChange={handleProviderChange}
              suffixIcon={
                selectedProvider && currentProvider ? (
                  currentProvider.available ? (
                    <Badge status="success" />
                  ) : (
                    <Badge status="error" />
                  )
                ) : undefined
              }
            >
              {llmProviders.map((provider) => (
                <Select.Option key={provider.id} value={provider.id}>
                  <Space>
                    <span>{provider.name}</span>
                    {provider.available ? (
                      <Badge status="success" text="Available" />
                    ) : (
                      <Badge status="error" text="Not configured" />
                    )}
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          {/* Model Selection */}
          {currentProvider && currentProvider.models.length > 0 && (
            <Form.Item label="Model" required>
              <Select
                style={{ width: 300 }}
                placeholder="Select a model"
                value={selectedModel || undefined}
                onChange={handleModelChange}
              >
                {currentProvider.models.map((model) => (
                  <Select.Option key={model.name} value={model.name}>
                    <Space direction="vertical" size={0}>
                      <span>{model.display_name}</span>
                      <Space size={4}>
                        {model.capabilities.map((cap) => {
                          const info = getCapabilityLabel(cap)
                          return (
                            <Tag key={cap} color={info.color} style={{ marginRight: 0, fontSize: 10 }}>
                              {info.label}
                            </Tag>
                          )
                        })}
                      </Space>
                    </Space>
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          )}

          {/* Model Details */}
          {currentModel && (
            <div style={{ marginTop: 16, padding: 16, backgroundColor: '#f5f5f5', borderRadius: 8 }}>
              <Descriptions size="small" column={2}>
                <Descriptions.Item label="Model">{currentModel.display_name}</Descriptions.Item>
                <Descriptions.Item label="Context Window">
                  {currentModel.context_window > 0 
                    ? `${(currentModel.context_window / 1000).toFixed(0)}K tokens` 
                    : 'Unknown'}
                </Descriptions.Item>
                <Descriptions.Item label="Capabilities" span={2}>
                  <Space wrap>
                    {currentModel.capabilities.map((cap) => {
                      const info = getCapabilityLabel(cap)
                      return (
                        <Tag key={cap} color={info.color}>
                          {info.label}
                        </Tag>
                      )
                    })}
                  </Space>
                </Descriptions.Item>
                {currentModel.description && (
                  <Descriptions.Item label="Description" span={2}>
                    <Text type="secondary">{currentModel.description}</Text>
                  </Descriptions.Item>
                )}
                {currentModel.pricing_hint && (
                  <Descriptions.Item label="Pricing" span={2}>
                    <Text type="secondary">{currentModel.pricing_hint}</Text>
                  </Descriptions.Item>
                )}
              </Descriptions>
            </div>
          )}

          {/* Provider Status */}
          {selectedProvider && currentProvider && !currentProvider.available && (
            <Alert
              type="warning"
              showIcon
              style={{ marginTop: 16 }}
              message="Provider not configured"
              description={
                <div>
                  <Text>Missing environment variables: </Text>
                  <Text code>{currentProvider.missing_env.join(', ')}</Text>
                </div>
              }
            />
          )}

          <Form.Item style={{ marginTop: 16 }}>
            <Button type="primary" htmlType="submit" loading={updateSettings.isPending}>
              {updateSettings.isPending ? '...' : t('common.save')}
            </Button>
          </Form.Item>
        </Form>

        {/* Usage Stats */}
        {llmStatus?.usage && (
          <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
            <Title level={5} style={{ marginBottom: 12 }}>Usage Today</Title>
            <Space size="large">
              <div>
                <Text type="secondary">Input Tokens: </Text>
                <Text strong>{llmStatus.usage.input_tokens?.toLocaleString() ?? 0}</Text>
              </div>
              <div>
                <Text type="secondary">Output Tokens: </Text>
                <Text strong>{llmStatus.usage.output_tokens?.toLocaleString() ?? 0}</Text>
              </div>
              <div>
                <Text type="secondary">Cost: </Text>
                <Text strong>${((llmStatus.usage.total_tokens ?? 0) * 0.00001).toFixed(4)}</Text>
              </div>
            </Space>
          </div>
        )}
      </Card>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginBottom: 16 }}>User Profile</Title>
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          Describe your background and interests to personalize recommendations. This will be used to extract your research interests using AI.
        </Text>
        <Input.TextArea
          value={profileContent}
          onChange={(e) => setProfileContent(e.target.value)}
          placeholder={`# My Profile

## Background
I am an AI researcher focused on medical applications.

## Research Interests
- Artificial Intelligence
- Machine Learning
- Medical AI
- Gene Editing

## Goals
Stay updated on latest AI research papers and biotech investments.
`}
          rows={10}
          style={{ marginBottom: 12, fontFamily: 'monospace' }}
        />
        <Space>
          <Button type="primary" onClick={handleSaveProfile} loading={saveUserProfile.isPending}>
            Save Profile
          </Button>
          {saveSuccess && <Text type="success">Profile saved and interests extracted!</Text>}
        </Space>
        {userProfile?.status?.is_empty === false && userProfile?.status?.content_length > 0 && (
          <div style={{ marginTop: 12 }}>
            <Text type="secondary">Extracted interests: </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              (Profile will be re-processed when saved)
            </Text>
          </div>
        )}
        {userProfile?.status?.is_empty && (
          <Alert
            type="info"
            showIcon
            style={{ marginTop: 12 }}
            message="No profile set yet. Fill in your profile above and click Save to personalize recommendations."
          />
        )}
      </Card>

      <Card size="small" title="Backup" extra={
        <Button size="small" onClick={handleBackup} loading={backup.isPending}>
          Download
        </Button>
      }>
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          Backup your feeds, entries, and settings.
        </Text>
        <input
          ref={fileRef}
          id="restore-file"
          type="file"
          accept=".json"
          style={{ display: 'none' }}
          onChange={handleRestore}
        />
        <Button onClick={() => fileRef.current?.click()} loading={restore.isPending}>
          Restore from Backup
        </Button>
      </Card>
    </div>
  )
}
