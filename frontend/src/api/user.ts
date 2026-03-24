import { apiUser } from './client'

export interface UserProfile {
  id: string
  email: string
  username?: string
  full_name?: string
  avatar_url?: string
  is_active: boolean
}

export function getUserProfile(userId: string) {
  return apiUser.get<UserProfile>(`/profiles/${userId}`)
}
