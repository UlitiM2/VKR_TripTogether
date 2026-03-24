import { apiTrip } from './client'

export interface Participant {
  user_id: string
  role: string
  invited_at: string
  accepted_at: string | null
}

export function getParticipants(tripId: string) {
  return apiTrip.get<Participant[]>(`/trips/${tripId}/participants`)
}

export function inviteParticipant(tripId: string, email: string) {
  return apiTrip.post(`/trips/${tripId}/participants/invite`, { email })
}

export function acceptInvitation(tripId: string) {
  return apiTrip.patch(`/trips/${tripId}/participants/me/accept`)
}
