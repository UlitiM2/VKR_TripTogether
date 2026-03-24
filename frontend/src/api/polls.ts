import { apiVoting } from './client'

export interface PollOption {
  id: string
  poll_id: string
  text: string
  position: number
  vote_count: number
}

export interface Poll {
  id: string
  trip_id: string
  created_by: string
  question: string
  options: PollOption[]
  my_option_id?: string | null
}

export interface PollCreate {
  question: string
  options: string[]
}

export function getPolls(tripId: string) {
  return apiVoting.get<Poll[]>(`/trips/${tripId}/polls`)
}

export function createPoll(tripId: string, data: PollCreate) {
  return apiVoting.post<Poll>(`/trips/${tripId}/polls`, data)
}

export function vote(tripId: string, pollId: string, optionId: string) {
  return apiVoting.post(`/trips/${tripId}/polls/${pollId}/vote`, { option_id: optionId })
}

export function deletePoll(tripId: string, pollId: string) {
  return apiVoting.delete(`/trips/${tripId}/polls/${pollId}`)
}
