import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useSettings, useUpdateSettings, useBackup, useRestore } from '../hooks/useSettings'
import { useQuery } from '@tanstack/react-query'
import { getHandlers } from '../api/settings'
import { useUIStore } from '../stores/uiStore'
import type { GlobalSettings } from '../types'
import { Card, Form, Input, Select, Button, Typography, Skeleton, Divider } from 'antd'

const { Title, Text } = Typography

export function Settings() {
  const { t, i18n } = useTranslation()
  const { data: settings, isLoading } = useSettings()
  const updateSettings = useUpdateSettings()
  const backup = useBackup()
  const restore = useRestore()
  const { data: handlers } = useQuery({
    queryKey: ['handlers'],
    queryFn: getHandlers,
  })
  const { setTheme } = useUIStore()
  const fileRef = useRef<HTMLInputElement>(null)
  const [form] = Form.useForm()

  const [formData, setFormData] = useState<Partial<GlobalSettings>>({})

  useEffect(() => {
    if (settings) {
      setFormData(settings)
      setTheme(settings.theme as any)
      form.setFieldsValue(settings)
    }
  }, [settings, form])

  const handleFinish = (values: Partial<GlobalSettings>) => {
    updateSettings.mutate({
      theme: values.theme ?? 'forest',
      refresh_interval: values.refresh_interval ?? 30,
      recent_hours: values.recent_hours ?? 24,
      reading_speed: values.reading_speed ?? 200,
      send_notification: values.send_notification ?? false,
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

  const handleLanguageChange = (lang: string) => {
    i18n.changeLanguage(lang)
    localStorage.setItem('language', lang)
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
          <Form.Item label={t('settings.language')} name="language">
            <Select style={{ width: 200 }} value={i18n.language} onChange={handleLanguageChange}>
              <Select.Option value="zh">{t('common.languageChinese')}</Select.Option>
              <Select.Option value="en">{t('common.languageEnglish')}</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label={t('settings.readingSpeed')} name="reading_speed">
            <Input type="number" min={100} max={1000} style={{ width: 120 }} />
          </Form.Item>

          <Form.Item label={t('settings.refreshInterval')} name="refresh_interval">
            <Input type="number" min={5} max={1440} style={{ width: 120 }} suffix="min" />
          </Form.Item>

          <Divider />

          <Title level={5} style={{ marginBottom: 16 }}>{t('settings.theme')}</Title>

          <Form.Item label="LLM" name="llm_handler_key">
            <Select style={{ width: 200 }} placeholder="Default">
              {llmHandlers.map((h) => (
                <Select.Option key={h.type} value={h.type}>{h.type}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="Content" name="content_retrieval_handler_key">
            <Select style={{ width: 200 }} placeholder="Default">
              {contentHandlers.map((h) => (
                <Select.Option key={h.type} value={h.type}>{h.type}</Select.Option>
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