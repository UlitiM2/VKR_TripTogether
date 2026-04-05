import axios, { type AxiosResponse, type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const getToken = () => localStorage.getItem('token')

export const apiAuth = axios.create({
  baseURL: '/api/auth',
  headers: { 'Content-Type': 'application/json' },
})

export const apiUser = axios.create({
  baseURL: '/api/user',
  headers: { 'Content-Type': 'application/json' },
})

export const apiTrip = axios.create({
  baseURL: '/api/trip',
  headers: { 'Content-Type': 'application/json' },
})

export const apiVoting = axios.create({
  baseURL: '/api/voting',
  headers: { 'Content-Type': 'application/json' },
})

export const apiBudget = axios.create({
  baseURL: '/api/budget',
  headers: { 'Content-Type': 'application/json' },
})

export const apiChat = axios.create({
  baseURL: '/api/chat',
  headers: { 'Content-Type': 'application/json' },
})

const withToken = (config: InternalAxiosRequestConfig) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}

const AUTH_PUBLIC_SEGMENTS = new Set(['login', 'register', 'forgot-password', 'reset-password'])

/** Не передавать старый JWT на публичные эндпоинты auth (логин/регистрация/сброс пароля). */
const withAuthApiToken = (config: InternalAxiosRequestConfig) => {
  const raw = config.url ?? ''
  const path = raw.split('?')[0]
  const lastSegment = path.split('/').filter(Boolean).pop() ?? ''
  if (AUTH_PUBLIC_SEGMENTS.has(lastSegment)) {
    return config
  }
  return withToken(config)
}

apiAuth.interceptors.request.use(withAuthApiToken)

;[apiUser, apiTrip, apiVoting, apiBudget, apiChat].forEach((api) => {
  api.interceptors.request.use(withToken)
  api.interceptors.response.use(
    (r: AxiosResponse) => r,
    (err: AxiosError) => {
      if (err.response?.status === 401) {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
      return Promise.reject(err)
    }
  )
})
