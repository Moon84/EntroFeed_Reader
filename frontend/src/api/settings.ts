import { apiGet, apiPost } from './client'
import type { GlobalSettings, AboutInfo, Handler } from '../types'

export async function getSettings(): Promise<GlobalSettings> {
  const data = await apiGet<GlobalSettings>('/api/about')
  return data as unknown as GlobalSettings
}

export async function getAbout(): Promise<AboutInfo & { settings: GlobalSettings }> {
  return apiGet('/api/about')
}

export interface UpdateSettingsParams {
  theme: string
  refresh_interval: number
  recent_hours: number
  reading_speed: number
  send_notification: boolean
  notification?: string
  llm?: string
  content?: string
  finished_onboarding?: boolean
}

export async function updateSettings(params: UpdateSettingsParams): Promise<void> {
  const form = new FormData()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined) form.append(k, String(v))
  })
  await apiPost('/api/update_settings/', form, true)
}

export async function getHandlers(): Promise<Handler[]> {
  return apiGet<Handler[]>('/util/list-handlers')
}

export async function getHandlerSchema(handler: string): Promise<unknown> {
  return apiGet(`/settings/${handler}`)
}

export async function updateHandler(handler: string, config: string): Promise<void> {
  const form = new FormData()
  form.append('handler', handler)
  form.append('config', config)
  await apiPost('/api/update_handler/', form, true)
}

export async function backup(): Promise<Blob> {
  const res = await fetch('/api/backup/')
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.blob()
}

export async function restore(file: File): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  await apiPost('/api/restore/', form, true)
}
