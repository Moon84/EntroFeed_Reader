import { createContext, useContext, useState, ReactNode, useCallback } from 'react'
import { updateEntryState } from '../client-api/entries'

interface FeedEntryStats {
  totalCount: number
  unreadCount: number
  importantCount: number // high score (>= 0.7)
  readCount: number
}

interface ReaderState {
  selectedFeedId: string | null
  setSelectedFeedId: (id: string | null) => void
  readEntryIds: Set<string>
  markAsRead: (id: string) => void
  markAllAsRead: (ids: string[]) => void
  likedEntries: Record<string, number> // entryId -> liked state (-1, 0, 1)
  toggleLike: (id: string) => void
  setDislike: (id: string) => void
  favoriteIds: Set<string>
  toggleFavorite: (id: string) => void
  // Per-feed stats calculated from loaded entries
  feedEntryStats: Record<string, FeedEntryStats>
  updateFeedStats: (feedId: string, entries: Array<{ id: string; total_score?: number }>) => void
  // Sync initial state from loaded entries
  syncStateFromEntries: (entries: Array<{ id: string; is_read?: boolean; liked?: number; is_favorite?: boolean }>) => void
}

const ReaderContext = createContext<ReaderState>({
  selectedFeedId: null,
  setSelectedFeedId: () => {},
  readEntryIds: new Set(),
  markAsRead: () => {},
  markAllAsRead: () => {},
  likedEntries: {},
  toggleLike: () => {},
  setDislike: () => {},
  favoriteIds: new Set(),
  toggleFavorite: () => {},
  feedEntryStats: {},
  updateFeedStats: () => {},
  syncStateFromEntries: () => {},
})

export function ReaderProvider({ children }: { children: ReactNode }) {
  const [selectedFeedId, setSelectedFeedId] = useState<string | null>(null)
  const [readEntryIds, setReadEntryIds] = useState<Set<string>>(new Set())
  const [likedEntries, setLikedEntries] = useState<Record<string, number>>({})
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set())
  const [feedEntryStats, setFeedEntryStats] = useState<Record<string, FeedEntryStats>>({})

  const markAsRead = useCallback((id: string) => {
    setReadEntryIds(prev => new Set(prev).add(id))
    // Persist to backend
    updateEntryState(id, { is_read: true }).catch(() => {})
  }, [])

  const markAllAsRead = useCallback((ids: string[]) => {
    setReadEntryIds(prev => {
      const next = new Set(prev)
      ids.forEach(id => next.add(id))
      return next
    })
    // Persist all to backend
    ids.forEach(id => updateEntryState(id, { is_read: true }).catch(() => {}))
  }, [])

  const toggleLike = useCallback((id: string) => {
    setLikedEntries(prev => {
      const current = prev[id] || 0
      // Toggle: 0 -> 1 (like), 1 -> 0 (unlike)
      const next = current === 1 ? 0 : 1
      // Persist to backend
      updateEntryState(id, { liked: next }).catch(() => {})
      return { ...prev, [id]: next }
    })
  }, [])

  const setDislike = useCallback((id: string) => {
    setLikedEntries(prev => {
      const current = prev[id] || 0
      // Toggle: 0 -> -1 (dislike), -1 -> 0 (remove dislike)
      const next = current === -1 ? 0 : -1
      // Persist to backend
      updateEntryState(id, { liked: next }).catch(() => {})
      return { ...prev, [id]: next }
    })
  }, [])

  const toggleFavorite = useCallback((id: string) => {
    setFavoriteIds(prev => {
      const next = new Set(prev)
      let newState = false
      if (next.has(id)) {
        next.delete(id)
        newState = false
      } else {
        next.add(id)
        newState = true
      }
      // Persist to backend
      updateEntryState(id, { is_favorite: newState }).catch(() => {})
      return next
    })
  }, [])

  const updateFeedStats = useCallback((feedId: string, entries: Array<{ id: string; total_score?: number }>) => {
    const totalCount = entries.length
    const readCount = entries.filter(e => readEntryIds.has(e.id)).length
    const importantCount = entries.filter(e => (e.total_score ?? 0) >= 0.7).length
    const unreadCount = totalCount - readCount

    setFeedEntryStats(prev => ({
      ...prev,
      [feedId]: { totalCount, unreadCount, importantCount, readCount }
    }))
  }, [readEntryIds])

  const syncStateFromEntries = useCallback((entries: Array<{ id: string; is_read?: boolean; liked?: number; is_favorite?: boolean }>) => {
    const readIds = new Set<string>()
    const liked: Record<string, number> = {}
    const favIds = new Set<string>()

    entries.forEach(e => {
      if (e.is_read) readIds.add(e.id)
      if (e.liked && e.liked !== 0) liked[e.id] = e.liked
      if (e.is_favorite) favIds.add(e.id)
    })

    setReadEntryIds(readIds)
    setLikedEntries(liked)
    setFavoriteIds(favIds)
  }, [])

  return (
    <ReaderContext.Provider value={{
      selectedFeedId,
      setSelectedFeedId,
      readEntryIds,
      markAsRead,
      markAllAsRead,
      likedEntries,
      toggleLike,
      setDislike,
      favoriteIds,
      toggleFavorite,
      feedEntryStats,
      updateFeedStats,
      syncStateFromEntries,
    }}>
      {children}
    </ReaderContext.Provider>
  )
}

export function useReader() {
  return useContext(ReaderContext)
}
