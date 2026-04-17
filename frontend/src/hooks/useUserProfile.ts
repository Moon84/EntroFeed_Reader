import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUserProfile, saveUserProfile, getUserProfileStatus } from '../client-api/settings'

export function useUserProfile() {
  return useQuery({
    queryKey: ['user-profile'],
    queryFn: getUserProfile,
  })
}

export function useUserProfileStatus() {
  return useQuery({
    queryKey: ['user-profile-status'],
    queryFn: getUserProfileStatus,
  })
}

export function useSaveUserProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (content: string) => saveUserProfile(content),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user-profile'] })
      qc.invalidateQueries({ queryKey: ['user-profile-status'] })
      qc.invalidateQueries({ queryKey: ['interests'] })
    },
  })
}
