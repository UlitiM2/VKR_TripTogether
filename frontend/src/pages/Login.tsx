import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { useAuth } from '../context/AuthContext'

function formatLoginError(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((x) =>
        typeof x === 'object' && x !== null && 'msg' in x ? String((x as { msg: unknown }).msg) : '',
      )
      .filter(Boolean)
    if (parts.length) return parts.join(' ')
  }
  return 'Ошибка входа'
}

export function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { login: setToken } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const { data } = await login(username, password)
      setToken(data.access_token)
      navigate('/')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setError(formatLoginError(detail))
    }
  }

  return (
    <div className="container" style={{ maxWidth: 400, marginTop: '3rem' }}>
      <div className="card">
        <h1 style={{ marginTop: 0 }}>Вход</h1>
        <form onSubmit={handleSubmit}>
          {error && <div className="error">{error}</div>}
          <label htmlFor="username">Email или имя пользователя</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="username"
          />
          <label htmlFor="password">Пароль</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
          <p style={{ margin: '-0.35rem 0 0.75rem', fontSize: '0.9rem' }}>
            <Link to="/forgot-password">Забыли пароль?</Link>
          </p>
          <button type="submit">Войти</button>
        </form>
        <p style={{ marginTop: '1rem' }}>
          Нет аккаунта? <Link to="/register">Регистрация</Link>
        </p>
      </div>
    </div>
  )
}
