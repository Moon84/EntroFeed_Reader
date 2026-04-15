import { useQuery } from '@tanstack/react-query'
import { getInterestRecommendations, getTrendingRecommendations, getSimilarRecommendations } from '../client-api/recommendations'
import type { Recommendation } from '../types'

export function useInterestRecommendations(limit = 20) {
  return useQuery<Recommendation[]>({
    queryKey: ['recommendations', 'interest', limit],
    queryFn: () => getInterestRecommendations(limit),
    staleTime: 5 * 60 * 1000,
  })
}

export function useTrendingRecommendations(limit = 20) {
  return useQuery<Recommendation[]>({
    queryKey: ['recommendations', 'trending', limit],
    queryFn: () => getTrendingRecommendations(limit),
    staleTime: 5 * 60 * 1000,
  })
}

export function useSimilarRecommendations(entryId: string, limit = 5) {
  return useQuery<Recommendation[]>({
    queryKey: ['recommendations', 'similar', entryId, limit],
    queryFn: () => getSimilarRecommendations(entryId, limit),
    enabled: !!entryId,
    staleTime: 5 * 60 * 1000,
  })
}
