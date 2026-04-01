import { useState, useEffect, useRef } from 'react'
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

function formatIsoDate(value: string): string {
  const parts = value.split('-')
  if (parts.length !== 3) return value
  const [year, month, day] = parts
  return `${day}.${month}.${year}`
}

async function reverseGeocodeCity(coords: [number, number]): Promise<string | null> {
  const [lat, lon] = coords
  const cacheKey = 'trip-map-reverse-city-cache-v1'
  try {
    const raw = localStorage.getItem(cacheKey)
    const cache = raw ? (JSON.parse(raw) as Record<string, string>) : {}
    const k = `${lat.toFixed(5)},${lon.toFixed(5)}`
    if (cache[k]) return cache[k]

    const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(
      String(lat),
    )}&lon=${encodeURIComponent(String(lon))}&accept-language=ru&zoom=10`
    const res = await fetch(url, {
      headers: {
        // Nominatim просит идентификацию; без этого иногда режет запросы.
        'User-Agent': 'TripTogether/1.0 (educational project)',
      },
    })
    if (!res.ok) return null
    const data = (await res.json()) as any
    const addr = data?.address || {}
    const city =
      addr.city ||
      addr.town ||
      addr.village ||
      addr.municipality ||
      addr.county ||
      null
    const cityStr = typeof city === 'string' ? city.trim() : ''
    if (!cityStr) return null

    cache[k] = cityStr
    localStorage.setItem(cacheKey, JSON.stringify(cache))
    return cityStr
  } catch {
    return null
  }
}

export function Trips() {
  const [trips, setTrips] = useState<Trip[]>([])
  const [markers, setMarkers] = useState<TripMapMarker[]>([])
  const [pickedCoords, setPickedCoords] = useState<[number, number] | null>(null)
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
  const destinationInputRef = useRef<HTMLInputElement | null>(null)
  const startDateInputRef = useRef<HTMLInputElement | null>(null)
  const endDateInputRef = useRef<HTMLInputElement | null>(null)

  function openNativeDatePicker(input: HTMLInputElement | null) {
    if (!input) return
    const withPicker = input as HTMLInputElement & { showPicker?: () => void }
    if (typeof withPicker.showPicker === 'function') {
      withPicker.showPicker()
      return
    }
    input.focus()
    input.click()
  }

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

  async function handleMapClick(e: any) {
    const coords = e?.get?.('coords') as [number, number] | undefined
    if (!coords) return
    setPickedCoords(coords)
    setShowForm(true)
    setTimeout(() => destinationInputRef.current?.focus(), 50)

    // Надежный fallback: reverse-geocode до города (OSM/Nominatim)
    const city = await reverseGeocodeCity(coords)
    if (city) {
      setForm((f) => ({ ...f, destination: city }))
      return
    }

    setForm((f) => ({ ...f, destination: `${coords[0].toFixed(5)}, ${coords[1].toFixed(5)}` }))
  }

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
                ref={destinationInputRef}
                value={form.destination}
                onChange={(e) => setForm((f) => ({ ...f, destination: e.target.value }))}
                placeholder="Например: Москва, Казань, Сочи"
              />
              <label>Дата начала</label>
              <div className="date-input-with-picker">
                <input
                  ref={startDateInputRef}
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                  required
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-compact"
                  onClick={() => openNativeDatePicker(startDateInputRef.current)}
                  aria-label="Открыть календарь даты начала"
                  title="Календарь"
                >
                  📅
                </button>
              </div>
              <label>Дата окончания</label>
              <div className="date-input-with-picker">
                <input
                  ref={endDateInputRef}
                  type="date"
                  value={form.end_date}
                  onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
                  required
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-compact"
                  onClick={() => openNativeDatePicker(endDateInputRef.current)}
                  aria-label="Открыть календарь даты окончания"
                  title="Календарь"
                >
                  📅
                </button>
              </div>
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
                    {formatIsoDate(t.start_date)} — {formatIsoDate(t.end_date)}
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
                onClick={handleMapClick}
                options={{
                  yandexMapDisablePoiInteractivity: true,
                  suppressMapOpenBlock: true,
                }}
                modules={['geoObject.addon.balloon', 'geoObject.addon.hint']}
              >
                {pickedCoords && (
                  <Placemark
                    geometry={pickedCoords}
                    properties={{
                      iconCaption: 'Новое направление',
                      hintContent: 'Нажмите на карту, чтобы выбрать место',
                    }}
                    options={{ preset: 'islands#violetDotIconWithCaption' }}
                  />
                )}
                {markers.map((m) => (
                  <Placemark
                    key={`${m.tripId}-${m.destination}`}
                    geometry={[m.lat, m.lon]}
                    properties={{
                      iconCaption: m.destination,
                      hintContent: m.destination,
                      balloonContentHeader: m.title,
                      balloonContentBody: `${m.destination}<br/>${formatIsoDate(m.startDate)} — ${formatIsoDate(m.endDate)}`,
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
