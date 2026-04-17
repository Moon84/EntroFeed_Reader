import { apiGet, apiPost } from './client'
import type { Feed } from '../types'

export async function listFeeds(): Promise<Feed[]> {
  return apiGet<Feed[]>('/util/list-feeds')
}

export interface FeedStats {
  feed_id: string
  total_count: number
  important_count: number
  unread_count: number
}

export async function getFeedStats(): Promise<FeedStats[]> {
  return apiGet<FeedStats[]>('/util/feed-stats')
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

export interface RSSHubRoute {
  title: string
  source: string
  target: string
  url: string
  full_url: string
}

export async function discoverRSSHub(url: string): Promise<RSSHubRoute[]> {
  return apiGet<RSSHubRoute[]>(`/util/discover-rsshub?url=${encodeURIComponent(url)}`)
}
