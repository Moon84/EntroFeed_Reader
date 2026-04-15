import { useQuery } from '@tanstack/react-query'
import { listFeedEntries } from '../client-api/entries'
import type { FeedEntry } from '../types'

export function useEntries(feedId?: string) {
  return useQuery<FeedEntry[]>({
    queryKey: ['entries', feedId],
    queryFn: () => listFeedEntries(feedId),
    staleTime: 1 * 60 * 1000,
  })
}

export function useRecentEntries() {
  return useQuery<FeedEntry[]>({
    queryKey: ['entries', 'recent'],
    queryFn: () => listFeedEntries(),
    staleTime: 1 * 60 * 1000,
  })
}
