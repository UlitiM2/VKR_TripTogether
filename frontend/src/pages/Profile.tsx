import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import { updateMe, uploadMyAvatar, changeMyPassword, formatUserDisplayName, type UserMe } from '../api/auth'
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
  return v.replace(/[^A-Za-zА-Яа-яЁё]/g, '')
}

function isLettersOnly(v: string) {
  return /^[A-Za-zА-Яа-яЁё]+$/.test(v.trim())
}

/** Обход кэша браузера для одного и того же URL файла аватара после замены файла на сервере */
function avatarUrlWithCacheBust(url: string | undefined | null, updatedAt?: string | null): string | undefined {
  if (!url) return undefined
  const ts = updatedAt ? new Date(updatedAt).getTime() : Date.now()
  if (Number.isNaN(ts)) return url
  const sep = url.includes('?') ? '&' : '?'
  return `${url}${sep}cb=${ts}`
}

const ACH_CARD_TINTS = [
  'profile-ach-card--t1',
  'profile-ach-card--t2',
  'profile-ach-card--t3',
  'profile-ach-card--t4',
]

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
  const inProgressCount = achievements.filter((a) => !a.unlocked).length
  const achievementsProgress = totalAchievements > 0 ? (completedAchievements / totalAchievements) * 100 : 0
  const [isAvatarChooserOpen, setIsAvatarChooserOpen] = useState(false)
  const [avatarUploading, setAvatarUploading] = useState(false)
  const [isAvatarUrlDialogOpen, setIsAvatarUrlDialogOpen] = useState(false)
  const [avatarUrlDialogValue, setAvatarUrlDialogValue] = useState('')
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [pwdCurrent, setPwdCurrent] = useState('')
  const [pwdNew, setPwdNew] = useState('')
  const [pwdNew2, setPwdNew2] = useState('')
  const [pwdSaving, setPwdSaving] = useState(false)
  const [pwdMessage, setPwdMessage] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  /** Снимаем readOnly после первого фокуса — меньше автоподстановки сохранённых паролей в Chrome. */
  const [pwdFormFocused, setPwdFormFocused] = useState(false)

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
      await updateMe({ avatar_url: '' })
      setAvatarUrl('')
      await refreshUser()
      setMessage({ type: 'ok', text: 'Аватар удалён' })
    } catch {
      setMessage({ type: 'err', text: 'Ошибка удаления аватара' })
    }
  }

  async function handleAvatarFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setMessage(null)
    setAvatarUploading(true)
    try {
      const { data } = await uploadMyAvatar(file)
      setAvatarUrl(data.avatar_url || '')
      await refreshUser()
      setIsAvatarChooserOpen(false)
      setMessage({ type: 'ok', text: 'Аватар обновлён' })
    } catch {
      setMessage({ type: 'err', text: 'Не удалось загрузить аватар' })
    } finally {
      setAvatarUploading(false)
      if (e.target) {
        e.target.value = ''
      }
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    setPwdMessage(null)
    if (pwdNew.length < 8) {
      setPwdMessage({ type: 'err', text: 'Новый пароль короче 8 символов.' })
      return
    }
    if (pwdNew !== pwdNew2) {
      setPwdMessage({ type: 'err', text: 'Новый пароль и повтор не совпадают.' })
      return
    }
    setPwdSaving(true)
    try {
      const { data } = await changeMyPassword(pwdCurrent, pwdNew)
      setPwdMessage({ type: 'ok', text: data.detail || 'Пароль обновлён' })
      setPwdCurrent('')
      setPwdNew('')
      setPwdNew2('')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      const text =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((x) => (typeof x === 'object' && x && 'msg' in x ? String((x as { msg: unknown }).msg) : '')).join(' ')
            : 'Не удалось сменить пароль'
      setPwdMessage({ type: 'err', text: text || 'Не удалось сменить пароль' })
    } finally {
      setPwdSaving(false)
    }
  }

  async function handleAvatarUrlConfirm() {
    const url = avatarUrlDialogValue.trim()
    if (!url) {
      setIsAvatarUrlDialogOpen(false)
      return
    }
    setMessage(null)
    try {
      await updateMe({ avatar_url: url })
      setAvatarUrl(url)
      await refreshUser()
      setIsAvatarUrlDialogOpen(false)
      setAvatarUrlDialogValue('')
      setMessage({ type: 'ok', text: 'Аватар обновлён' })
    } catch {
      setMessage({ type: 'err', text: 'Не удалось установить аватар по ссылке' })
    }
  }

  if (!user) return null

  const displayName = formatUserDisplayName(user)
  const greetingName = fullName.trim() || displayName.split(' ')[0] || displayName

  function renderAvatarBlock(u: UserMe, className?: string) {
    return (
      <div className={className ?? 'profile-hero__avatar-wrap'}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleAvatarFileSelected}
        />
        {u.avatar_url ? (
          <div className="profile-avatar-placeholder-wrapper profile-avatar-placeholder-wrapper--hero">
            <img
              src={avatarUrlWithCacheBust(u.avatar_url, u.updated_at)}
              alt=""
              className="profile-avatar-hero"
              onClick={() => setIsAvatarChooserOpen((open) => !open)}
            />
            {isAvatarChooserOpen && (
              <div className="profile-avatar-picker">
                <button
                  type="button"
                  className="btn btn-danger btn-compact profile-avatar-picker__btn"
                  onClick={handleRemoveAvatar}
                >
                  Удалить аватар
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="profile-avatar-placeholder-wrapper profile-avatar-placeholder-wrapper--hero">
            <button
              type="button"
              className="profile-avatar-placeholder profile-avatar-placeholder--hero"
              aria-label="Добавить аватар"
              onClick={() => setIsAvatarChooserOpen((open) => !open)}
            >
              +
            </button>
            {isAvatarChooserOpen && (
              <div className="profile-avatar-picker">
                <button
                  type="button"
                  className="btn btn-secondary btn-compact profile-avatar-picker__btn"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={avatarUploading}
                >
                  {avatarUploading ? 'Загрузка...' : 'Из файла'}
                </button>
                <button
                  type="button"
                  className="btn btn-compact profile-avatar-picker__btn profile-avatar-picker__btn--ghost"
                  onClick={() => {
                    setIsAvatarUrlDialogOpen(true)
                    setAvatarUrlDialogValue('')
                    setIsAvatarChooserOpen(false)
                  }}
                >
                  По ссылке
                </button>
              </div>
            )}
            {isAvatarUrlDialogOpen && (
              <div className="profile-avatar-url-dialog">
                <input
                  id="avatarUrlInline"
                  type="url"
                  className="profile-avatar-url-input"
                  placeholder="https://..."
                  value={avatarUrlDialogValue}
                  onChange={(e) => setAvatarUrlDialogValue(e.target.value)}
                />
                <div className="profile-avatar-url-actions">
                  <button type="button" className="btn btn-secondary btn-compact" onClick={handleAvatarUrlConfirm}>
                    ОК
                  </button>
                  <button
                    type="button"
                    className="btn btn-compact profile-avatar-picker__btn--ghost"
                    onClick={() => {
                      setIsAvatarUrlDialogOpen(false)
                      setAvatarUrlDialogValue('')
                    }}
                  >
                    Отмена
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="profile-dashboard">
      <header className="profile-dashboard__top">
        <h1 className="profile-dashboard__page-title">Профиль</h1>
      </header>

      <section className="profile-hero">
        <div className="profile-hero__text">
          <p className="profile-hero__kicker">TripTogether</p>
          <h2 className="profile-hero__title">Привет, {greetingName}!</h2>
          <p className="profile-hero__lead">
            Собирайте достижения за поездки, голосования и бюджет — ниже вся ваша статистика в одном месте.
          </p>
        </div>
        {renderAvatarBlock(user)}
      </section>

      <section className="profile-achievements-main" aria-labelledby="profile-ach-heading">
        <div className="profile-achievements-main__head">
          <h2 id="profile-ach-heading" className="profile-achievements-main__title">
            Достижения
          </h2>
          <p className="profile-achievements-main__subtitle">
            Выполняйте задания, создавайте поездки, голосуйте и ведите бюджет.
          </p>
        </div>

        <div className="profile-metric-row">
          <article className="profile-metric-card">
            <span className="profile-metric-card__label">Получено</span>
            <span className="profile-metric-card__value">{completedAchievements}</span>
            <span className="profile-metric-card__hint">из {totalAchievements || '—'}</span>
          </article>
          <article className="profile-metric-card profile-metric-card--accent">
            <span className="profile-metric-card__label">В процессе</span>
            <span className="profile-metric-card__value">{inProgressCount}</span>
            <span className="profile-metric-card__hint">активных целей</span>
          </article>
          <article className="profile-metric-card">
            <span className="profile-metric-card__label">Общий прогресс</span>
            <span className="profile-metric-card__value">{Math.round(achievementsProgress)}%</span>
            <div className="profile-metric-card__bar" aria-hidden>
              <span className="profile-metric-card__bar-fill" style={{ width: `${achievementsProgress}%` }} />
            </div>
          </article>
        </div>

        {achievements.length === 0 ? (
          <p className="profile-ach-empty">Достижения появятся после активности в поездках.</p>
        ) : (
          <ul className="profile-ach-card-grid">
            {achievements.map((a, i) => {
              const done = a.unlocked
              const tint = ACH_CARD_TINTS[i % ACH_CARD_TINTS.length]
              return (
                <li
                  key={a.id}
                  className={`profile-ach-card ${tint}${done ? ' is-done' : ''}`}
                  data-requirement={a.requirement}
                >
                  <div className="profile-ach-card__top">
                    <span className="profile-ach-card__icon" aria-hidden>
                      {a.icon}
                    </span>
                    <span className={`profile-ach-card__badge${done ? ' is-done' : ''}`}>
                      {done ? 'Получено' : 'В процессе'}
                    </span>
                  </div>
                  <h3 className="profile-ach-card__name">{a.title}</h3>
                  <p className="profile-ach-card__stat">
                    {done ? 'Цель выполнена' : `${a.current} / ${a.target}`}
                  </p>
                  <div className="profile-ach-card__progress">
                    <span
                      className="profile-ach-card__progress-fill"
                      style={{ width: `${Math.max(0, Math.min(100, a.progress))}%` }}
                    />
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section className="profile-settings-card" aria-labelledby="profile-settings-heading">
        <h3 id="profile-settings-heading" className="profile-settings-card__title">
          Данные аккаунта
        </h3>
        <p className="profile-settings-card__hint">Имя, фамилия и email для входа и отображения</p>
        <form className="profile-settings-form" onSubmit={handleSubmit}>
          <div className="profile-settings-form__grid">
            <div>
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
            </div>
            <div>
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
            </div>
          </div>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            className="profile-email-input"
            value={emailDraft}
            onChange={(e) => setEmailDraft(e.target.value)}
            type="email"
            autoComplete="email"
          />
          <div className="profile-settings-form__actions">
            <button type="submit" className="btn">
              Сохранить
            </button>
          </div>
        </form>
      </section>

      <section className="profile-settings-card" aria-labelledby="profile-password-heading">
        <h3 id="profile-password-heading" className="profile-settings-card__title">
          Смена пароля
        </h3>
        <form
          className="profile-settings-form profile-settings-form--password"
          onSubmit={handleChangePassword}
          autoComplete="off"
          onFocusCapture={() => setPwdFormFocused(true)}
        >
          <label htmlFor="pwd-current">Текущий пароль</label>
          <input
            id="pwd-current"
            name="profile-change-current"
            type="password"
            value={pwdCurrent}
            onChange={(e) => setPwdCurrent(e.target.value)}
            autoComplete="off"
            readOnly={!pwdFormFocused}
            disabled={pwdSaving}
          />
          <label htmlFor="pwd-new">Новый пароль</label>
          <input
            id="pwd-new"
            name="profile-change-new"
            type="password"
            value={pwdNew}
            onChange={(e) => setPwdNew(e.target.value)}
            autoComplete="off"
            readOnly={!pwdFormFocused}
            minLength={8}
            disabled={pwdSaving}
          />
          <label htmlFor="pwd-new2">Повторите новый пароль</label>
          <input
            id="pwd-new2"
            name="profile-change-new2"
            type="password"
            value={pwdNew2}
            onChange={(e) => setPwdNew2(e.target.value)}
            autoComplete="off"
            readOnly={!pwdFormFocused}
            minLength={8}
            disabled={pwdSaving}
          />
          {pwdMessage && (
            <div className={pwdMessage.type === 'ok' ? 'success' : 'error'} style={{ marginBottom: '0.5rem' }}>
              {pwdMessage.text}
            </div>
          )}
          <div className="profile-settings-form__actions">
            <button type="submit" className="btn btn-secondary" disabled={pwdSaving}>
              {pwdSaving ? 'Сохранение…' : 'Обновить пароль'}
            </button>
          </div>
        </form>
      </section>

      {message && (
        <div className="profile-message-row profile-message-row--dashboard">
          <div className={message.type === 'ok' ? 'success' : 'error'}>{message.text}</div>
        </div>
      )}
    </div>
  )
}
