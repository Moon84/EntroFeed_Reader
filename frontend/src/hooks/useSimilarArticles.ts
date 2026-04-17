import { useQuery } from '@tanstack/react-query'
import { getSimilarRecommendations } from '../client-api/recommendations'
import type { Recommendation } from '../types'

export function useSimilarRecommendations(entryId: string, limit = 5) {
  return useQuery<Recommendation[]>({
    queryKey: ['recommendations', 'similar', entryId, limit],
    queryFn: () => getSimilarRecommendations(entryId, limit),
    enabled: !!entryId,
    staleTime: 5 * 60 * 1000,
  })
}