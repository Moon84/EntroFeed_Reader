import { apiGet, apiPost } from './client'
import type { GlobalSettings, AboutInfo, Handler } from '../types'

export async function getSettings(): Promise<GlobalSettings> {
  const data = await apiGet<{version: string; python_version: string; fastapi_version: string; docker: boolean; storage_handler: string; github: string; settings: GlobalSettings}>('/api/about')
  return data.settings
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

// ============ User Profile (user.md) ============

export interface UserProfileStatus {
  exists: boolean
  is_empty: boolean
  content_length: number
  path: string
}

export interface UserProfileResponse {
  content: string
  status: UserProfileStatus
}

export async function getUserProfile(): Promise<UserProfileResponse> {
  return apiGet<UserProfileResponse>('/api/user/profile')
}

export async function saveUserProfile(content: string): Promise<{ success: boolean; interests: unknown[]; count: number }> {
  const res = await fetch('/api/user/profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function getUserProfileStatus(): Promise<UserProfileStatus> {
  return apiGet<UserProfileStatus>('/api/user/profile/status')
}
