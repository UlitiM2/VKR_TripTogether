import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { updateMe } from '../api/auth'

function splitFullName(full: string): { first: string; last: string } {
  const t = (full || '').trim()
  if (!t) return { first: '', last: '' }
  const i = t.indexOf(' ')
  if (i === -1) return { first: t, last: '' }
  return { first: t.slice(0, i), last: t.slice(i + 1).trim() }
}

function joinFullName(first: string, last: string) {
  return [first.trim(), last.trim()].filter(Boolean).join(' ')
}

export function Profile() {
  const { user, refreshUser } = useAuth()
  const [fullName, setFullName] = useState('')
  const [lastName, setLastName] = useState('')
  const [avatarUrl, setAvatarUrl] = useState('')
  const [message, setMessage] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  useEffect(() => {
    if (user) {
      const { first, last } = splitFullName(user.full_name || '')
      setFullName(first)
      setLastName(last)
      setAvatarUrl(user.avatar_url || '')
    }
  }, [user])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setMessage(null)
    try {
      const combined = joinFullName(fullName, lastName)
      await updateMe({ full_name: combined || undefined, avatar_url: avatarUrl || undefined })
      await refreshUser()
      setMessage({ type: 'ok', text: 'Профиль обновлён' })
    } catch {
      setMessage({ type: 'err', text: 'Ошибка сохранения' })
    }
  }

  async function handleRemoveAvatar() {
    setMessage(null)
    try {
      await updateMe({ avatar_url: null })
      setAvatarUrl('')
      await refreshUser()
      setMessage({ type: 'ok', text: 'Аватар удалён' })
    } catch {
      setMessage({ type: 'err', text: 'Ошибка удаления аватара' })
    }
  }

  if (!user) return null

  return (
    <>
      <div className="page-header">
        <h1>Профиль</h1>
      </div>
      <div className="card">
        <p><strong>Email:</strong> {user.email}</p>
        {user.avatar_url && (
          <p>
            <img src={user.avatar_url} alt="Аватар" className="profile-avatar-preview" />
            <br />
            <button type="button" className="btn btn-danger btn-compact profile-remove-avatar-btn" onClick={handleRemoveAvatar}>
              Удалить аватар
            </button>
          </p>
        )}
        <form onSubmit={handleSubmit}>
          {message && (
            <div className={message.type === 'ok' ? 'success' : 'error'}>{message.text}</div>
          )}
          <label htmlFor="fullName">Имя</label>
          <input
            id="fullName"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            autoComplete="given-name"
          />
          <label htmlFor="lastName">Фамилия</label>
          <input
            id="lastName"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            autoComplete="family-name"
          />
          <label htmlFor="avatarUrl">URL аватара</label>
          <input
            id="avatarUrl"
            type="url"
            value={avatarUrl}
            onChange={(e) => setAvatarUrl(e.target.value)}
            placeholder="https://..."
          />
          <button type="submit">Сохранить</button>
        </form>
      </div>
    </>
  )
}
