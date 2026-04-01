import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { getPolls, createPoll, vote, deletePoll, type Poll } from '../api/polls'

const POLLS_UPDATED_EVENT = 'trip-polls-updated'

function notifyPollsUpdated(tripId: string) {
  window.dispatchEvent(new CustomEvent(POLLS_UPDATED_EVENT, { detail: { tripId } }))
}

export function TripPollsCreate({ tripId }: { tripId: string }) {
  const [question, setQuestion] = useState('')
  const [options, setOptions] = useState<string[]>(['', ''])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    const cleanOptions = options.map((s) => s.trim()).filter(Boolean)
    if (cleanOptions.length < 2) return
    try {
      await createPoll(tripId, { question: question.trim(), options: cleanOptions })
      setQuestion('')
      setOptions(['', ''])
      notifyPollsUpdated(tripId)
    } catch (err) {
      console.error(err)
    }
  }

  function updateOption(idx: number, value: string) {
    setOptions((prev) => prev.map((item, i) => (i === idx ? value : item)))
  }

  function addOptionField() {
    setOptions((prev) => [...prev, ''])
  }

  function removeOptionField(idx: number) {
    setOptions((prev) => (prev.length <= 2 ? prev : prev.filter((_, i) => i !== idx)))
  }

  return (
    <div className="card board-widget board-widget--polls">
      <form className="board-widget__form" onSubmit={handleCreate}>
        <label>Вопрос</label>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} required />
        <label>Варианты</label>
        <div className="poll-create-options">
          {options.map((opt, idx) => (
            <div key={`poll-option-input-${idx}`} className="poll-create-options__row">
              <input
                value={opt}
                onChange={(e) => updateOption(idx, e.target.value)}
                placeholder={`Вариант ${idx + 1}`}
                required={idx < 2}
              />
              <button
                type="button"
                className="btn btn-secondary btn-compact"
                onClick={() => removeOptionField(idx)}
                disabled={options.length <= 2}
                aria-label="Удалить вариант"
                title="Удалить вариант"
              >
                ✕
              </button>
            </div>
          ))}
          <button type="button" className="btn btn-secondary btn-compact" onClick={addOptionField}>
            + Добавить вариант
          </button>
        </div>
        <button type="submit">Создать опрос</button>
      </form>
    </div>
  )
}

export function TripPollsResults({ tripId }: { tripId: string }) {
  const { user } = useAuth()
  const [polls, setPolls] = useState<Poll[]>([])
  const [loading, setLoading] = useState(true)

  function getTopOptionText(poll: Poll) {
    if (poll.options.length === 0) return 'нет вариантов'
    const winner = [...poll.options].sort((a, b) => b.vote_count - a.vote_count)[0]
    return winner?.text || 'нет вариантов'
  }

  function getTopOption(poll: Poll) {
    if (poll.options.length === 0) return null
    return [...poll.options].sort((a, b) => b.vote_count - a.vote_count)[0] || null
  }

  async function load() {
    try {
      const { data } = await getPolls(tripId)
      setPolls(data)
    } catch {
      setPolls([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [tripId])

  useEffect(() => {
    function onUpdated(e: Event) {
      const ce = e as CustomEvent<{ tripId?: string }>
      if (ce.detail?.tripId === tripId) load()
    }
    window.addEventListener(POLLS_UPDATED_EVENT, onUpdated)
    return () => window.removeEventListener(POLLS_UPDATED_EVENT, onUpdated)
  }, [tripId])

  async function handleVote(pollId: string, optionId: string) {
    try {
      await vote(tripId, pollId, optionId)
      notifyPollsUpdated(tripId)
      load()
    } catch (err) {
      console.error(err)
    }
  }

  async function handleDeletePoll(pollId: string) {
    if (!confirm('Удалить этот опрос?')) return
    try {
      await deletePoll(tripId, pollId)
      notifyPollsUpdated(tripId)
      load()
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) return <div className="loading">Загрузка...</div>

  return (
    <div className="card board-widget board-widget--polls">
      {polls.length > 0 && (
        <div className="poll-summary-simple">
          {polls.map((poll) => (
            <p key={`summary-${poll.id}`} className="poll-summary-simple__line">
              <span className="poll-summary-simple__q">{poll.question}</span>
              <span className="poll-summary-simple__a">🏆 {getTopOptionText(poll)}</span>
            </p>
          ))}
        </div>
      )}

      <div className="poll-list-simple">
        {polls.map((poll) => (
          <div key={poll.id} className="poll-card-simple">
            <div className="poll-card-simple__head">
              <strong className="poll-card-simple__question">{poll.question}</strong>
              {user?.id === poll.created_by && (
                <button type="button" className="btn btn-danger btn-compact" onClick={() => handleDeletePoll(poll.id)}>
                  ✕
                </button>
              )}
            </div>
            <ul className="poll-card-simple__options">
              {poll.options.map((opt) => (
                <li
                  key={opt.id}
                  className={`poll-option-simple ${poll.my_option_id === opt.id ? 'poll-option-simple--voted' : ''}`}
                  onClick={() => handleVote(poll.id, opt.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      handleVote(poll.id, opt.id)
                    }
                  }}
                >
                  <span className="poll-option-simple__text">
                    {opt.text}
                    <span className="poll-option-simple__count">{opt.vote_count}</span>
                  </span>
                  <div
                    className="poll-option-simple__bar"
                    style={{
                      width: `${Math.max(
                        8,
                        Math.round((opt.vote_count / Math.max(1, getTopOption(poll)?.vote_count || 1)) * 100),
                      )}%`,
                    }}
                  />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
