import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { getPolls, createPoll, vote, deletePoll, type Poll } from '../api/polls'

export function TripPolls({ tripId }: { tripId: string }) {
  const { user } = useAuth()
  const [polls, setPolls] = useState<Poll[]>([])
  const [loading, setLoading] = useState(true)
  const [question, setQuestion] = useState('')
  const [optionsText, setOptionsText] = useState('')
  const [collapsed, setCollapsed] = useState(false)

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

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    const options = optionsText.split('\n').map((s) => s.trim()).filter(Boolean)
    if (options.length < 2) return
    try {
      await createPoll(tripId, { question, options })
      setQuestion('')
      setOptionsText('')
      load()
    } catch (err) {
      console.error(err)
    }
  }

  async function handleVote(pollId: string, optionId: string) {
    try {
      await vote(tripId, pollId, optionId)
      load()
    } catch (err) {
      console.error(err)
    }
  }

  async function handleDeletePoll(pollId: string) {
    if (!confirm('Удалить этот опрос?')) return
    try {
      await deletePoll(tripId, pollId)
      load()
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) return <div className="loading">Загрузка...</div>

  return (
    <div className="card board-widget board-widget--polls">
      <div className="poll-head-simple">
        <h2>Голосования</h2>
        <button type="button" className="btn btn-secondary btn-compact" onClick={() => setCollapsed((v) => !v)}>
          {collapsed ? 'Развернуть' : 'Свернуть'}
        </button>
      </div>

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

      {!collapsed && (
        <>
          <form className="board-widget__form" onSubmit={handleCreate}>
            <label>Вопрос</label>
            <input value={question} onChange={(e) => setQuestion(e.target.value)} required />
            <label>Варианты (каждый с новой строки)</label>
            <textarea
              value={optionsText}
              onChange={(e) => setOptionsText(e.target.value)}
              placeholder="Вариант 1&#10;Вариант 2"
              rows={3}
              required
            />
            <button type="submit">Создать опрос</button>
          </form>
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
        </>
      )}
    </div>
  )
}
