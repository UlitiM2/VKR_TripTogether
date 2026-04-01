import { apiUser } from './client'

export interface UserProfile {
  id: string
  email: string
  username?: string
  full_name?: string
  avatar_url?: string
  is_active: boolean
}

export interface AchievementItem {
  id: string
  icon: string
  title: string
  requirement: string
  current: number
  target: number
  progress: number
  unlocked: boolean
}

export interface AchievementListResponse {
  achievements: AchievementItem[]
}

export function getUserProfile(userId: string) {
  return apiUser.get<UserProfile>(`/profiles/${userId}`)
}

export function getMyAchievements() {
  return apiUser.get<AchievementListResponse>('/profiles/me/achievements')
}

export type TripDashboardLayout = {
  layouts: unknown
  collapsed: Record<string, boolean>
}

export function getTripDashboardLayout(tripId: string) {
  return apiUser.get<TripDashboardLayout>(`/profiles/me/trip-layouts/${tripId}`)
}

export function saveTripDashboardLayout(tripId: string, payload: TripDashboardLayout) {
  return apiUser.put<TripDashboardLayout>(`/profiles/me/trip-layouts/${tripId}`, payload)
}
