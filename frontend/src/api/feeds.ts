import { apiGet, apiPost } from './client'
import type { Feed } from '../types'

export async function listFeeds(): Promise<Feed[]> {
  return apiGet<Feed[]>('/util/list-feeds')
}

export async function refreshFeed(feedId: string): Promise<void> {
  await apiPost(`/api/refresh_feed/${feedId}`)
}

export async function deleteFeed(feedId: string): Promise<void> {
  await apiPost(`/api/delete_feed/${feedId}`)
}

export interface FeedFormData {
  name: string
  url: string
  category: string
  notify_destination?: string
  notify?: boolean
  preview_only?: boolean
  refresh_enabled?: boolean
  use_script?: boolean
  retrieve_content?: boolean
}

export async function updateFeed(data: FeedFormData): Promise<void> {
  const form = new FormData()
  Object.entries(data).forEach(([k, v]) => {
    if (v !== undefined) form.append(k, String(v))
  })
  await apiPost('/api/update_feed/', form, true)
}

export async function importOpml(file: File): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  await apiPost('/api/import_opml/', form, true)
}

export async function exportOpml(): Promise<Blob> {
  const res = await fetch('/api/export_opml/')
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.blob()
}
