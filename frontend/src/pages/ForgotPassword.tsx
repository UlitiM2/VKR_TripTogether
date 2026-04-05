import { useState } from 'react'
import { Link } from 'react-router-dom'
import { requestPasswordReset } from '../api/auth'

export function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setMessage('')
    setSubmitting(true)
    try {
      const { data } = await requestPasswordReset(email.trim())
      setMessage(data.detail || 'Запрос обработан.')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Не удалось отправить запрос')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container" style={{ maxWidth: 400, marginTop: '3rem' }}>
      <div className="card">
        <h1 style={{ marginTop: 0 }}>Забыли пароль?</h1>
        <p style={{ marginTop: 0, color: '#64748b', fontSize: '0.95rem', lineHeight: 1.45 }}>
          Укажите email аккаунта. Если он зарегистрирован, придёт письмо со ссылкой на сброс (действует около часа).
        </p>
        <form onSubmit={handleSubmit}>
          {error && <div className="error">{error}</div>}
          {message && (
            <div className="success" style={{ marginBottom: '0.75rem' }}>
              {message}
            </div>
          )}
          <label htmlFor="forgot-email">Email</label>
          <input
            id="forgot-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            disabled={submitting}
          />
          <button type="submit" disabled={submitting}>
            {submitting ? 'Отправка…' : 'Отправить ссылку'}
          </button>
        </form>
        <p style={{ marginTop: '1rem' }}>
          <Link to="/login">← Назад ко входу</Link>
        </p>
      </div>
    </div>
  )
}
