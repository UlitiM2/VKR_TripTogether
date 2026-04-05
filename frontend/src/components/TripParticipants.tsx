import { useState, useEffect } from 'react'
import { getParticipants, inviteParticipant, acceptInvitation, type Participant } from '../api/participants'
import { getUserProfile } from '../api/user'
import { useAuth } from '../context/AuthContext'

function shortId(id: string) {
  return id.length > 10 ? `${id.slice(0, 8)}…` : id
}

type ParticipantMeta = {
  name: string
  avatarUrl?: string
}

export function TripParticipants({ tripId }: { tripId: string }) {
  const { user } = useAuth()
  const [list, setList] = useState<Participant[]>([])
  const [metaByUserId, setMetaByUserId] = useState<Record<string, ParticipantMeta>>({})
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [accepting, setAccepting] = useState(false)
  const [acceptError, setAcceptError] = useState('')

  async function load() {
    try {
      const { data } = await getParticipants(tripId)
      setList(data)
    } catch {
      setList([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [tripId])

  useEffect(() => {
    const ids = Array.from(new Set(list.map((p) => p.user_id)))
    if (ids.length === 0) {
      setMetaByUserId({})
      return
    }
    Promise.all(
      ids.map(async (id) => {
        try {
          const { data } = await getUserProfile(id)
          const name = data.full_name?.trim() || data.username?.trim() || data.email?.trim() || shortId(id)
          return [id, { name, avatarUrl: data.avatar_url }] as const
        } catch {
          return [id, { name: shortId(id) }] as const
        }
      }),
    ).then((pairs) => {
      setMetaByUserId(Object.fromEntries(pairs))
    })
  }, [list])

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await inviteParticipant(tripId, email)
      setEmail('')
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Ошибка приглашения')
    }
  }

  async function handleAcceptInvite() {
    setAcceptError('')
    setAccepting(true)
    try {
      await acceptInvitation(tripId)
      await load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setAcceptError(typeof msg === 'string' ? msg : 'Не удалось принять приглашение')
    } finally {
      setAccepting(false)
    }
  }

  const myPending = user?.id
    ? list.find((p) => p.user_id === user.id && !p.accepted_at)
    : undefined

  if (loading) return <div className="loading">Загрузка...</div>

  return (
    <div className="card board-widget board-widget--people">
      {myPending && (
        <div className="trip-invite-banner" role="status">
          <p className="trip-invite-banner__text">
            Вас пригласили в эту поездку. Нажмите «Принять», чтобы закрепить участие — до этого в списке отображается статус «приглашён».
          </p>
          {acceptError && <div className="error trip-invite-banner__err">{acceptError}</div>}
          <button
            type="button"
            className="btn trip-invite-banner__btn"
            disabled={accepting}
            onClick={handleAcceptInvite}
          >
            {accepting ? 'Сохранение…' : 'Принять приглашение'}
          </button>
        </div>
      )}
      <ul className="participant-list-simple">
        {list.map((p) => (
          <li key={p.user_id} className="participant-item-simple">
            {metaByUserId[p.user_id]?.avatarUrl ? (
              <img
                src={metaByUserId[p.user_id].avatarUrl}
                alt={metaByUserId[p.user_id].name}
                className="participant-avatar participant-avatar--image"
              />
            ) : (
              <span className="participant-avatar" aria-hidden />
            )}
            {' '}
            <span className="participant-name-simple">{metaByUserId[p.user_id]?.name || shortId(p.user_id)}</span>
            <span className="participant-role-simple">{p.role}</span>
            <span className="participant-status-simple">{p.accepted_at ? '✓' : '(приглашён)'}</span>
          </li>
        ))}
      </ul>
      <form className="board-widget__form" onSubmit={handleInvite}>
        {error && <div className="error">{error}</div>}
        <label>Пригласить по email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email@example.com"
          required
        />
        <button type="submit">Пригласить</button>
      </form>
    </div>
  )
}
