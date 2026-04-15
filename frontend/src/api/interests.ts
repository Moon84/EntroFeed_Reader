import { apiGet, apiPostJson, apiDelete, apiPatch } from './client'
import type { UserInterest } from '../types'

export async function listInterests(category?: string): Promise<UserInterest[]> {
  const url = category ? `/api/interests?category=${category}` : '/api/interests'
  const data = await apiGet<{ interests: UserInterest[] }>(url)
  return data.interests
}

export async function addInterest(
  name: string,
  category: string,
  priority = 3,
): Promise<UserInterest> {
  const data = await apiPostJson<{ interest: UserInterest }>('/api/interests', {
    name,
    category,
    priority,
  })
  return data.interest
}

export async function removeInterest(interestId: string): Promise<void> {
  await apiDelete(`/api/interests/${interestId}`)
}

export async function updateInterestPriority(
  interestId: string,
  priority: number,
): Promise<UserInterest> {
  return apiPatch<UserInterest>(`/api/interests/${interestId}`, { priority })
}

export async function getInferredInterests(limit = 5): Promise<UserInterest[]> {
  const data = await apiGet<{ inferred: UserInterest[] }>(`/api/interests/inferred?limit=${limit}`)
  return data.inferred
}

export async function acceptInferredInterest(tag: string, priority = 2): Promise<UserInterest> {
  return apiPostJson<UserInterest>(`/api/interests/inferred/${encodeURIComponent(tag)}`, {
    priority,
  })
}
