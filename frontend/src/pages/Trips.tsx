import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getTrips, createTrip, deleteTrip, type Trip, type TripCreate } from '../api/trips'
import { YMaps, Map as YMap, Placemark } from '@pbe/react-yandex-maps'

type TripMapMarker = {
  tripId: string
  title: string
  destination: string
  startDate: string
  endDate: string
  lat: number
  lon: number
}

export function Trips() {
  const [trips, setTrips] = useState<Trip[]>([])
  const [markers, setMarkers] = useState<TripMapMarker[]>([])
  const [mapRef, setMapRef] = useState<{
    setCenter: (center: [number, number], zoom?: number, options?: Record<string, unknown>) => void
    setBounds: (bounds: [[number, number], [number, number]], options?: Record<string, unknown>) => void
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [mapLoading, setMapLoading] = useState(false)
  const [mapError, setMapError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<TripCreate>({
    title: '',
    destination: '',
    start_date: '',
    end_date: '',
    description: '',
  })

  async function load() {
    try {
      const { data } = await getTrips()
      setTrips(data)
    } catch {
      setTrips([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    const destinations = Array.from(
      new Set(
        trips
          .map((t) => (t.destination || '').trim())
          .filter((d) => d.length > 1),
      ),
    )
    if (destinations.length === 0) {
      setMarkers([])
      setMapError('')
      return
    }

    let cancelled = false

    async function geocodeDestinations() {
      setMapLoading(true)
      setMapError('')
      const cacheKey = 'trip-map-geocode-cache-v1'
      const fromStorage = localStorage.getItem(cacheKey)
      const cache = fromStorage ? JSON.parse(fromStorage) as Record<string, { lat: number; lon: number }> : {}
      const destinationCoords: Record<string, { lat: number; lon: number }> = {}

      for (const destination of destinations.slice(0, 50)) {
        if (cache[destination]) {
          destinationCoords[destination] = cache[destination]
          continue
        }
        try {
          const response = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(destination)}`,
          )
          if (!response.ok) continue
          const results = await response.json() as Array<{ lat: string; lon: string }>
          const first = results[0]
          if (!first) continue
          const lat = Number(first.lat)
          const lon = Number(first.lon)
          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue
          const coords = { lat, lon }
          destinationCoords[destination] = coords
          cache[destination] = coords
        } catch {
          // ignore individual geocoding failures
        }
      }

      localStorage.setItem(cacheKey, JSON.stringify(cache))
      if (cancelled) return

      const nextMarkers = trips
        .map((t) => {
          const destination = (t.destination || '').trim()
          const coords = destinationCoords[destination]
          if (!coords || destination.length <= 1) return null
          return {
            tripId: t.id,
            title: t.title,
            destination,
            startDate: t.start_date,
            endDate: t.end_date,
            lat: coords.lat,
            lon: coords.lon,
          } satisfies TripMapMarker
        })
        .filter((v): v is TripMapMarker => v !== null)

      setMarkers(nextMarkers)
      if (nextMarkers.length === 0) {
        setMapError('Не удалось определить координаты направлений. Укажите более точные места в поездках.')
      }
      setMapLoading(false)
    }

    geocodeDestinations()

    return () => {
      cancelled = true
    }
  }, [trips])

  useEffect(() => {
    if (!mapRef || markers.length === 0) return
    if (markers.length === 1) {
      mapRef.setCenter([markers[0].lat, markers[0].lon], 8, { duration: 260 })
      return
    }

    const lats = markers.map((m) => m.lat)
    const lons = markers.map((m) => m.lon)
    const southWest: [number, number] = [Math.min(...lats), Math.min(...lons)]
    const northEast: [number, number] = [Math.max(...lats), Math.max(...lons)]
    mapRef.setBounds([southWest, northEast], {
      checkZoomRange: true,
      zoomMargin: 30,
      duration: 280,
    })
  }, [markers, mapRef])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await createTrip({
        ...form,
        destination: form.destination || undefined,
        description: form.description || undefined,
      })
      setShowForm(false)
      setForm({ title: '', destination: '', start_date: '', end_date: '', description: '' })
      load()
    } catch (err) {
      console.error(err)
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Удалить поездку?')) return
    try {
      await deleteTrip(id)
      load()
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) return <div className="loading">Загрузка поездок...</div>

  return (
    <div className="trips-layout">
      <section className="trips-panel">
        <div className="page-header">
          <h1>Мои поездки</h1>
          <button type="button" className="btn" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Отмена' : '+ Новая поездка'}
          </button>
        </div>

        {showForm && (
          <div className="card">
            <h2>Создать поездку</h2>
            <form onSubmit={handleCreate}>
              <label>Название</label>
              <input
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                required
              />
              <label>Направление</label>
              <input
                value={form.destination}
                onChange={(e) => setForm((f) => ({ ...f, destination: e.target.value }))}
                placeholder="Например: Москва, Казань, Сочи"
              />
              <label>Дата начала</label>
              <input
                type="date"
                value={form.start_date}
                onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                required
              />
              <label>Дата окончания</label>
              <input
                type="date"
                value={form.end_date}
                onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
                required
              />
              <label>Описание</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              />
              <button type="submit">Создать</button>
            </form>
          </div>
        )}

        <div className="trips-list">
          {trips.length === 0 && !showForm ? (
            <div className="card">Пока нет поездок. Создайте первую.</div>
          ) : (
            trips.map((t) => (
              <div key={t.id} className="card trip-card">
                <div>
                  <h2>
                    <Link to={`/trip/${t.id}`}>{t.title}</Link>
                  </h2>
                  {((t.destination || '').trim().length > 1) && (
                    <p className="trip-card__meta">{(t.destination || '').trim()}</p>
                  )}
                  <p className="trip-card__dates">
                    {t.start_date} — {t.end_date}
                  </p>
                </div>
                <button type="button" className="btn btn-danger" onClick={() => handleDelete(t.id)}>
                  Удалить
                </button>
              </div>
            ))
          )}
        </div>
      </section>

      <aside className="card trips-map-panel">
        <div className="trips-map-panel__head">
          <h2>Карта поездок</h2>
          <p>Отмечайте места, где вы уже были в рамках поездок</p>
        </div>

        <div className="trips-map-wrap">
          {mapLoading ? (
            <div className="trips-map-empty">Загружаю отметки на карте...</div>
          ) : markers.length === 0 ? (
            <div className="trips-map-empty">
              {mapError || 'Добавьте направления в поездках, и они появятся на карте.'}
            </div>
          ) : (
            <YMaps query={{ lang: 'ru_RU' }}>
              <YMap
                defaultState={{ center: [55.751244, 37.618423], zoom: 4 }}
                className="trips-map"
                instanceRef={setMapRef}
                options={{
                  yandexMapDisablePoiInteractivity: true,
                  suppressMapOpenBlock: true,
                }}
                modules={['geoObject.addon.balloon', 'geoObject.addon.hint']}
              >
                {markers.map((m) => (
                  <Placemark
                    key={`${m.tripId}-${m.destination}`}
                    geometry={[m.lat, m.lon]}
                    properties={{
                      iconCaption: m.destination,
                      hintContent: m.destination,
                      balloonContentHeader: m.title,
                      balloonContentBody: `${m.destination}<br/>${m.startDate} — ${m.endDate}`,
                      balloonContentFooter: `<a href="/trip/${m.tripId}">Открыть поездку</a>`,
                    }}
                    options={{
                      preset: 'islands#blueDotIconWithCaption',
                    }}
                  />
                ))}
              </YMap>
            </YMaps>
          )}
        </div>
      </aside>
    </div>
  )
}
