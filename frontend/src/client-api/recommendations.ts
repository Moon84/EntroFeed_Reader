import { apiGet } from './client'
import type { Recommendation } from '../types'

export async function getInterestRecommendations(limit = 10): Promise<Recommendation[]> {
  const data = await apiGet<{ recommendations: Recommendation[] }>(
    `/api/recommendations/interest?limit=${limit}`,
  )
  return data.recommendations
}

export async function getTrendingRecommendations(limit = 10): Promise<Recommendation[]> {
  const data = await apiGet<{ recommendations: Recommendation[] }>(
    `/api/recommendations/trending?limit=${limit}`,
  )
  return data.recommendations
}

export async function getSimilarRecommendations(
  entryId: string,
  limit = 5,
): Promise<Recommendation[]> {
  const data = await apiGet<{ recommendations: Recommendation[] }>(
    `/api/recommendations/similar/${entryId}?limit=${limit}`,
  )
  return data.recommendations
}
