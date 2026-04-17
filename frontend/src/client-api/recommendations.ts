import { apiGet } from './client'
import type { Recommendation } from '../types'

export interface RecommendationsResponse {
  recommendations: Recommendation[]
}

export async function getSimilarRecommendations(entryId: string, limit = 5): Promise<Recommendation[]> {
  const data = await apiGet<RecommendationsResponse>(`/api/recommendations/similar/${entryId}?limit=${limit}`)
  return data.recommendations
}

export async function getInterestRecommendations(limit = 10): Promise<Recommendation[]> {
  const data = await apiGet<RecommendationsResponse>(`/api/recommendations/interest?limit=${limit}`)
  return data.recommendations
}

export async function getTrendingRecommendations(limit = 10): Promise<Recommendation[]> {
  const data = await apiGet<RecommendationsResponse>(`/api/recommendations/trending?limit=${limit}`)
  return data.recommendations
}