import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useSettings, useUpdateSettings, useBackup, useRestore } from '../hooks/useSettings'
import { useUserProfile, useSaveUserProfile } from '../hooks/useUserProfile'
import { useQuery } from '@tanstack/react-query'
import { getHandlers } from '../client-api/settings'
import { getLLMStatus } from '../client-api/entries'
import { useUIStore } from '../stores/uiStore'
import type { GlobalSettings } from '../types'
import { Card, Form, Input, Select, Button, Typography, Skeleton, Divider, Alert, Space } from 'antd'

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
  const { setTheme } = useUIStore()
  const fileRef = useRef<HTMLInputElement>(null)
  const [form] = Form.useForm()
  const [profileContent, setProfileContent] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)

  const [formData, setFormData] = useState<Partial<GlobalSettings>>({})
  const [effectiveLlM, setEffectiveLlM] = useState<string>('')

  useEffect(() => {
    if (settings) {
      // When llm_handler_key is null_llm, show the actual provider in the UI
      const effective = settings.llm_handler_key === 'null_llm'
        ? (llmStatus?.provider || 'null_llm')
        : settings.llm_handler_key
      setEffectiveLlM(effective)
      const formValues = { ...settings, llm_handler_key: effective }
      setFormData(formValues)
      setTheme(settings.theme as any)
      form.setFieldsValue(formValues)
    }
  }, [settings, form, llmStatus])

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

  const handleFinish = (values: Partial<GlobalSettings>) => {
    // When the form shows the effective provider (because llm_handler_key was null_llm),
    // convert it back to null_llm on save — unless the user explicitly changed it.
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

  const llmHandlers = handlers?.filter((h) => h.type === 'llm') ?? []
  const contentHandlers = handlers?.filter((h) => h.type === 'content') ?? []

  if (isLoading) {
    return (
      <div>
        <Skeleton active paragraph={{ rows: 6 }} />
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 640 }}>
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

          <Form.Item label="LLM" name="llm_handler_key">
            <Select style={{ width: 200 }} placeholder="Default">
              {llmHandlers.map((h) => (
                <Select.Option key={h.name} value={h.name}>{h.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>

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