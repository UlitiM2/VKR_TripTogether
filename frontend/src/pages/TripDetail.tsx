import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getTrip, updateTrip, type Trip } from '../api/trips'
import { TripParticipants } from '../components/TripParticipants'
import { TripPolls } from '../components/TripPolls'
import { TripExpenses } from '../components/TripExpenses'
import { TripChat } from '../components/TripChat'

function formatDateRange(start: string, end: string) {
  const s = new Date(start)
  const e = new Date(end)
  const opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' }
  return `${s.toLocaleDateString('ru-RU', opts)} — ${e.toLocaleDateString('ru-RU', opts)}`
}

export function TripDetail() {
  const { tripId } = useParams<{ tripId: string }>()
  const [trip, setTrip] = useState<Trip | null>(null)
  const [titleDraft, setTitleDraft] = useState('')
  const [destinationDraft, setDestinationDraft] = useState('')
  const [startDateDraft, setStartDateDraft] = useState('')
  const [endDateDraft, setEndDateDraft] = useState('')
  const [editingTrip, setEditingTrip] = useState(false)
  const [tripSaving, setTripSaving] = useState(false)
  const [tripError, setTripError] = useState('')

  useEffect(() => {
    if (!tripId) return
    getTrip(tripId)
      .then(({ data }) => {
        setTrip(data)
        setTitleDraft(data.title)
        setDestinationDraft(data.destination || '')
        setStartDateDraft(data.start_date)
        setEndDateDraft(data.end_date)
      })
      .catch(() => setTrip(null))
  }, [tripId])

  function startEditTrip() {
    if (!trip) return
    setTitleDraft(trip.title)
    setDestinationDraft(trip.destination || '')
    setStartDateDraft(trip.start_date)
    setEndDateDraft(trip.end_date)
    setTripError('')
    setEditingTrip(true)
  }

  function cancelEditTrip() {
    if (trip) {
      setTitleDraft(trip.title)
      setDestinationDraft(trip.destination || '')
      setStartDateDraft(trip.start_date)
      setEndDateDraft(trip.end_date)
    }
    setTripError('')
    setEditingTrip(false)
  }

  async function saveTrip() {
    if (!tripId || !trip) return
    const nextTitle = titleDraft.trim()
    if (!nextTitle) {
      setTripError('Введите название')
      return
    }
    if (!startDateDraft || !endDateDraft) {
      setTripError('Укажите даты поездки')
      return
    }
    if (new Date(startDateDraft).getTime() > new Date(endDateDraft).getTime()) {
      setTripError('Дата начала не может быть позже даты окончания')
      return
    }
    setTripError('')
    setTripSaving(true)
    try {
      const { data } = await updateTrip(tripId, {
        title: nextTitle,
        destination: destinationDraft.trim() || null,
        start_date: startDateDraft,
        end_date: endDateDraft,
      })
      setTrip(data)
      setTitleDraft(data.title)
      setDestinationDraft(data.destination || '')
      setStartDateDraft(data.start_date)
      setEndDateDraft(data.end_date)
      setEditingTrip(false)
    } catch {
      setTripError('Не удалось сохранить')
    } finally {
      setTripSaving(false)
    }
  }

  if (!tripId) return <div>Нет поездки</div>
  if (!trip) return <div className="loading">Загрузка...</div>

  const canEditTrip = trip.is_organizer === true
  const destination = trip.destination?.trim() || ''
  const showDestination = destination.length > 1

  return (
    <div className="whiteboard-page">
      <Link to="/trips" className="whiteboard-back">← Поездки</Link>

      <div className="whiteboard">
        <header className="board-header">
          <div className="board-title-row">
            {editingTrip ? (
              <div className="board-title-edit">
                <input
                  className="board-title-input"
                  value={titleDraft}
                  onChange={(e) => setTitleDraft(e.target.value)}
                  disabled={tripSaving}
                  autoFocus
                  aria-label="Название поездки"
                />
                <label htmlFor="trip-destination" className="board-edit-label">Направление</label>
                <input
                  id="trip-destination"
                  className="board-title-input board-title-input--secondary"
                  value={destinationDraft}
                  onChange={(e) => setDestinationDraft(e.target.value)}
                  disabled={tripSaving}
                  placeholder="Например: Москва"
                  aria-label="Направление поездки"
                />
                <div className="form-row-2">
                  <div>
                    <label htmlFor="trip-start-date">Дата начала</label>
                    <input
                      id="trip-start-date"
                      type="date"
                      value={startDateDraft}
                      onChange={(e) => setStartDateDraft(e.target.value)}
                      disabled={tripSaving}
                    />
                  </div>
                  <div>
                    <label htmlFor="trip-end-date">Дата окончания</label>
                    <input
                      id="trip-end-date"
                      type="date"
                      value={endDateDraft}
                      onChange={(e) => setEndDateDraft(e.target.value)}
                      disabled={tripSaving}
                    />
                  </div>
                </div>
                <div className="board-title-actions">
                  <button type="button" className="btn btn-compact" onClick={saveTrip} disabled={tripSaving}>
                    {tripSaving ? 'Сохранение…' : 'Сохранить'}
                  </button>
                  <button type="button" className="btn-text" onClick={cancelEditTrip} disabled={tripSaving}>
                    Отмена
                  </button>
                </div>
                {tripError && <p className="board-title-error">{tripError}</p>}
              </div>
            ) : (
              <>
                <h1 className="board-title">{trip.title}</h1>
                {canEditTrip && (
                  <button type="button" className="btn-edit-title" onClick={startEditTrip}>
                    Изменить
                  </button>
                )}
              </>
            )}
          </div>
          {showDestination && <p className="board-destination">{destination}</p>}
          <div className="board-dates">
            <span className="board-dates-label">Даты</span>
            <span className="board-dates-value">{formatDateRange(trip.start_date, trip.end_date)}</span>
          </div>
          {trip.description && (
            <p className="board-description">{trip.description}</p>
          )}
        </header>

        <div className="board-grid">
          <section className="board-cell board-cell--participants">
            <TripParticipants tripId={tripId} />
          </section>
          <section className="board-cell board-cell--polls">
            <TripPolls tripId={tripId} />
          </section>
          <section className="board-cell board-cell--expenses">
            <TripExpenses tripId={tripId} />
          </section>
          <section className="board-cell board-cell--chat">
            <TripChat tripId={tripId} />
          </section>
        </div>
      </div>
    </div>
  )
}
