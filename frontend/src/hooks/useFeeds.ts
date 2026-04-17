import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listFeeds, refreshFeed, deleteFeed, updateFeed, importOpml, exportOpml, getFeedStats, type FeedFormData, type FeedStats } from '../client-api/feeds'
import type { Feed } from '../types'

export function useFeeds() {
  return useQuery<Feed[]>({
    queryKey: ['feeds'],
    queryFn: listFeeds,
    staleTime: 5 * 60 * 1000,
  })
}

export function useFeedStats() {
  return useQuery<FeedStats[]>({
    queryKey: ['feed-stats'],
    queryFn: getFeedStats,
    staleTime: 30000, // Refresh every 30 seconds
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  })
}

export function useRefreshFeed() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: refreshFeed,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['feeds'] })
      qc.invalidateQueries({ queryKey: ['entries'] })
    },
  })
}

export function useDeleteFeed() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: deleteFeed,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['feeds'] })
    },
  })
}

export function useUpdateFeed() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: FeedFormData) => updateFeed(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['feeds'] })
    },
  })
}

export function useImportOpml() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: importOpml,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['feeds'] })
    },
  })
}

export function useExportOpml() {
  return useMutation({
    mutationFn: exportOpml,
  })
}
