import { apiTrip } from './client'

export interface Trip {
  id: string
  title: string
  destination?: string
  start_date: string
  end_date: string
  budget?: string
  description?: string
  created_by: string
  created_at: string
  updated_at: string
  is_organizer?: boolean
}

export interface TripCreate {
  title: string
  destination?: string
  start_date: string
  end_date: string
  budget?: string
  description?: string
}

export function getTrips() {
  return apiTrip.get<Trip[]>('/trips')
}

export function getTrip(id: string) {
  return apiTrip.get<Trip>(`/trips/${id}`)
}

export function createTrip(data: TripCreate) {
  return apiTrip.post<Trip>('/trips', data)
}

export function deleteTrip(id: string) {
  return apiTrip.delete(`/trips/${id}`)
}

export function updateTrip(
  id: string,
  data: { title?: string; destination?: string | null; start_date?: string; end_date?: string; description?: string | null },
) {
  return apiTrip.patch<Trip>(`/trips/${id}`, data)
}
