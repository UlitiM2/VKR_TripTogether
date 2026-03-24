import { apiChat } from './client'

export interface Message {
  id: string
  trip_id: string
  author_user_id: string
  content: string
  created_at: string
}

export function getMessages(tripId: string, limit = 100, offset = 0) {
  return apiChat.get<Message[]>(`/trips/${tripId}/messages`, { params: { limit, offset } })
}

export function sendMessage(tripId: string, content: string) {
  return apiChat.post<Message>(`/trips/${tripId}/messages`, { content })
}

export function getChatWebSocketUrl(tripId: string): string {
  const base = window.location.origin.replace(/^http/, 'ws')
  const token = localStorage.getItem('token')
  return `${base}/api/chat/trips/${tripId}/messages/ws${token ? `?token=${encodeURIComponent(token)}` : ''}`
}
