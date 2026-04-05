import { apiAuth } from './client'

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface UserMe {
  id: string
  email: string
  username?: string
  full_name?: string
  avatar_url?: string
  is_active: boolean
  is_verified: boolean
  created_at: string
  updated_at: string
}

export interface RegisterBody {
  email: string
  username?: string
  full_name?: string
  password: string
}

export function formatUserDisplayName(
  user: Pick<UserMe, 'full_name' | 'email' | 'username'> | null | undefined,
): string {
  if (!user) return 'Пользователь'
  const name = user.full_name?.trim()
  if (name) return name
  return user.email || user.username || 'Пользователь'
}

export function requestPasswordReset(email: string) {
  return apiAuth.post<{ detail: string }>('/forgot-password', { email })
}

export function resetPasswordWithToken(token: string, newPassword: string) {
  return apiAuth.post<{ detail: string }>('/reset-password', {
    token,
    new_password: newPassword,
  })
}

export function login(username: string, password: string) {
  const body = new URLSearchParams()
  body.set('username', username.trim())
  body.set('password', password)
  return apiAuth.post<LoginResponse>('/login', body.toString(), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export function register(data: RegisterBody) {
  return apiAuth.post<UserMe>('/register', data)
}

export function getMe() {
  return apiAuth.get<UserMe>('/me')
}

export function updateMe(data: { full_name?: string; email?: string | null; avatar_url?: string | null }) {
  return apiAuth.patch<UserMe>('/me', data)
}

export function changeMyPassword(currentPassword: string, newPassword: string) {
  return apiAuth.post<{ detail: string }>('/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

export function uploadMyAvatar(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return apiAuth.post<UserMe>('/me/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
