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

apiAuth.interceptors.request.use(withToken)

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
