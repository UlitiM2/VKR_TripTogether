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

export function login(username: string, password: string) {
  const params = new URLSearchParams()
  params.append('username', username)
  params.append('password', password)
  return apiAuth.post<LoginResponse>('/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export function register(data: RegisterBody) {
  return apiAuth.post<UserMe>('/register', data)
}

export function getMe() {
  return apiAuth.get<UserMe>('/me')
}

export function updateMe(data: { full_name?: string; avatar_url?: string | null }) {
  return apiAuth.patch<UserMe>('/me', data)
}
