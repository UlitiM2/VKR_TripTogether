import { useState, useMemo } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { resetPasswordWithToken } from '../api/auth'

export function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const tokenFromUrl = useMemo(() => (searchParams.get('token') || '').trim(), [searchParams])

  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!tokenFromUrl) {
      setError('В ссылке нет ключа. Запросите новое письмо со страницы «Забыли пароль».')
      return
    }
    if (password.length < 8) {
      setError('Пароль короче 8 символов.')
      return
    }
    if (password !== password2) {
      setError('Пароли не совпадают.')
      return
    }
    setSubmitting(true)
    try {
      const { data } = await resetPasswordWithToken(tokenFromUrl, password)
      setMessage(data.detail || 'Пароль изменён.')
      setTimeout(() => navigate('/login', { replace: true }), 1500)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Ссылка недействительна или устарела. Запросите новую.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container" style={{ maxWidth: 400, marginTop: '3rem' }}>
      <div className="card">
        <h1 style={{ marginTop: 0 }}>Новый пароль</h1>
        {!tokenFromUrl && (
          <div className="error" style={{ marginBottom: '0.75rem' }}>
            Ссылка неполная. Откройте адрес из письма или{' '}
            <Link to="/forgot-password">запросите сброс снова</Link>.
          </div>
        )}
        <form onSubmit={handleSubmit}>
          {error && <div className="error">{error}</div>}
          {message && (
            <div className="success" style={{ marginBottom: '0.75rem' }}>
              {message}
            </div>
          )}
          <label htmlFor="reset-pass">Новый пароль</label>
          <input
            id="reset-pass"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
            disabled={submitting || !tokenFromUrl}
          />
          <label htmlFor="reset-pass2">Повторите пароль</label>
          <input
            id="reset-pass2"
            type="password"
            value={password2}
            onChange={(e) => setPassword2(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
            disabled={submitting || !tokenFromUrl}
          />
          <button type="submit" disabled={submitting || !tokenFromUrl}>
            {submitting ? 'Сохранение…' : 'Сохранить пароль'}
          </button>
        </form>
        <p style={{ marginTop: '1rem' }}>
          <Link to="/login">← Ко входу</Link>
        </p>
      </div>
    </div>
  )
}
