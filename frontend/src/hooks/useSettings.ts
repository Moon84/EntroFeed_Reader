import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateSettings, backup, restore, type UpdateSettingsParams } from '../api/settings'

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
    staleTime: 5 * 60 * 1000,
  })
}

export function useUpdateSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params: UpdateSettingsParams) => updateSettings(params),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

export function useBackup() {
  return useMutation({ mutationFn: backup })
}

export function useRestore() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: restore,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}
