import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { updateMe } from '../api/auth'
import { getMyAchievements, type AchievementItem } from '../api/user'

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

function sanitizeLettersOnly(v: string) {
  // Разрешаем только буквы (RU/EN + Ё/ё). Остальные символы убираем.
  return v.replace(/[^A-Za-zА-Яа-яЁё]/g, '')
}

function isLettersOnly(v: string) {
  return /^[A-Za-zА-Яа-яЁё]+$/.test(v.trim())
}

export function Profile() {
  const { user, refreshUser } = useAuth()
  const [fullName, setFullName] = useState('')
  const [lastName, setLastName] = useState('')
  const [emailDraft, setEmailDraft] = useState('')
  const [avatarUrl, setAvatarUrl] = useState('')
  const [fullNameError, setFullNameError] = useState('')
  const [lastNameError, setLastNameError] = useState('')
  const [message, setMessage] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const [achievements, setAchievements] = useState<AchievementItem[]>([])
  const completedAchievements = achievements.filter((a) => a.unlocked).length
  const totalAchievements = achievements.length
  const achievementsProgress = totalAchievements > 0 ? (completedAchievements / totalAchievements) * 100 : 0

  useEffect(() => {
    if (user) {
      const { first, last } = splitFullName(user.full_name || '')
      setFullName(sanitizeLettersOnly(first))
      setLastName(sanitizeLettersOnly(last))
      setEmailDraft(user.email || '')
      setAvatarUrl(user.avatar_url || '')
      setFullNameError('')
      setLastNameError('')
    }
  }, [user])

  useEffect(() => {
    let cancelled = false
    getMyAchievements()
      .then(({ data }) => {
        if (!cancelled) setAchievements(data.achievements || [])
      })
      .catch(() => {
        if (!cancelled) setAchievements([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setMessage(null)
    setFullNameError('')
    setLastNameError('')
    try {
      const f = sanitizeLettersOnly(fullName)
      const l = sanitizeLettersOnly(lastName)
      if (!f) {
        setFullNameError('Введите имя (только буквы).')
        return
      }
      if (!l) {
        setLastNameError('Введите фамилию (только буквы).')
        return
      }
      if (!isLettersOnly(f) || !isLettersOnly(l)) {
        setFullNameError('Можно только буквы.')
        setLastNameError('Можно только буквы.')
        return
      }

      const combined = joinFullName(f, l)
      await updateMe({
        full_name: combined || undefined,
        email: emailDraft.trim() || undefined,
        avatar_url: avatarUrl || undefined,
      })
      await refreshUser()
      setMessage({ type: 'ok', text: 'Профиль обновлён' })
    } catch {
      setMessage({ type: 'err', text: 'Ошибка сохранения' })
    }
  }

  async function handleRemoveAvatar() {
    setMessage(null)
    try {
      // На практике безопаснее передавать пустую строку: фронт воспринимает '' как "аватара нет",
      // а бэкенд обычно без проблем принимает её как Optional[str].
      await updateMe({ avatar_url: '' })
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
      <div className="page-header profile-page-header">
        <h1>Профиль</h1>
      </div>
      <div className="card profile-card">
        <div className="profile-layout">
          <div className="profile-form-col">
            <form onSubmit={handleSubmit}>
              {message && (
                <div className={message.type === 'ok' ? 'success' : 'error'}>{message.text}</div>
              )}

              <label htmlFor="fullName">Имя</label>
              <input
                id="fullName"
                value={fullName}
                onChange={(e) => {
                  setFullName(sanitizeLettersOnly(e.target.value))
                  setFullNameError('')
                }}
                autoComplete="given-name"
              />
              {fullNameError && <div className="field-error">{fullNameError}</div>}

              <label htmlFor="lastName">Фамилия</label>
              <input
                id="lastName"
                value={lastName}
                onChange={(e) => {
                  setLastName(sanitizeLettersOnly(e.target.value))
                  setLastNameError('')
                }}
                autoComplete="family-name"
              />
              {lastNameError && <div className="field-error">{lastNameError}</div>}

              <label htmlFor="email">Email</label>
              <input
                id="email"
                className="profile-email-input"
                value={emailDraft}
                onChange={(e) => setEmailDraft(e.target.value)}
                type="email"
                autoComplete="email"
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

          <div className="profile-avatar-col">
            {user.avatar_url ? (
              <>
                <img
                  src={user.avatar_url}
                  alt="Аватар"
                  className="profile-avatar-preview profile-avatar-preview--right"
                />
                <button
                  type="button"
                  className="btn btn-danger btn-compact profile-remove-avatar-btn"
                  onClick={handleRemoveAvatar}
                >
                  Удалить аватар
                </button>
              </>
            ) : (
              <div className="profile-avatar-placeholder" aria-label="Аватар не установлен">
                Аватар не установлен
              </div>
            )}
          </div>

          <aside className="profile-achievements-col">
            <div className="profile-achievements">
              <h3 className="profile-achievements__title">Достижения</h3>
              <div className="profile-achievements__summary">
                <span className="profile-achievements__summary-count">{completedAchievements}/{totalAchievements}</span>
                <div className="profile-achievements__summary-progress" aria-label="Общий прогресс достижений">
                  <span className="profile-achievements__summary-progress-fill" style={{ width: `${achievementsProgress}%` }} />
                </div>
              </div>
              <ul className="profile-achievements__list">
                {achievements.map((a) => {
                  const done = a.unlocked
                  return (
                    <li
                      key={a.id}
                      className={`profile-achievements__item${done ? ' is-done' : ''}`}
                      data-requirement={a.requirement}
                    >
                      <div className="profile-achievements__row">
                        <span className="profile-achievements__icon" aria-hidden>{a.icon}</span>
                        <span className="profile-achievements__name">{a.title}</span>
                        <span className={`profile-achievements__status${done ? ' is-done' : ''}`}>
                          {done ? 'Получено' : 'В процессе'}
                        </span>
                      </div>
                      <div className="profile-achievements__progress">
                        <span className="profile-achievements__progress-fill" style={{ width: `${Math.max(0, Math.min(100, a.progress))}%` }} />
                      </div>
                      <div className="profile-achievements__item-count">{a.current}/{a.target}</div>
                    </li>
                  )
                })}
              </ul>
            </div>
          </aside>
        </div>
      </div>
    </>
  )
}
