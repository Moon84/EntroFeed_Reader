import { create } from 'zustand'

interface UIStore {
  sidebarOpen: boolean
  theme: string
  setSidebarOpen: (open: boolean) => void
  toggleSidebar: () => void
  setTheme: (theme: string) => void
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: false,
  theme: 'forest',
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setTheme: (theme) => {
    document.documentElement.setAttribute('data-theme', theme)
    set({ theme })
  },
}))
