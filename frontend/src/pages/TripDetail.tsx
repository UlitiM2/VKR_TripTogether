import { useMemo, useRef, useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getTrip, updateTrip, type Trip } from '../api/trips'
import { TripParticipants } from '../components/TripParticipants'
import { TripPollsCreate, TripPollsResults } from '../components/TripPolls'
import { TripExpensesSummary, TripExpensesCreate, TripExpensesHistory } from '../components/TripExpenses'
import { TripChat } from '../components/TripChat'
import { getTripDashboardLayout, saveTripDashboardLayout } from '../api/user'
import { ReactGridLayout } from 'react-grid-layout'

function formatDateRange(start: string, end: string) {
  const formatIsoDate = (value: string) => {
    const parts = value.split('-')
    if (parts.length !== 3) return value
    const [year, month, day] = parts
    return `${day}.${month}.${year}`
  }
  return `${formatIsoDate(start)} — ${formatIsoDate(end)}`
}

// react-grid-layout typings vary across versions; define minimal layout types locally.
type RGLLayoutItem = {
  i: string
  x: number
  y: number
  w: number
  h: number
  minW?: number
  minH?: number
  [key: string]: unknown
}

type Layouts = Record<string, RGLLayoutItem[]>
const DashboardGrid = ReactGridLayout as any

type WidgetId = 'participants' | 'pollsCreate' | 'pollsResults' | 'expensesSummary' | 'expensesCreate' | 'expensesHistory' | 'chat'
const ALL_BREAKPOINTS = ['lg', 'md', 'sm', 'xs', 'xxs'] as const
const DASH_WIDGETS: WidgetId[] = ['participants', 'pollsCreate', 'pollsResults', 'expensesSummary', 'expensesCreate', 'expensesHistory', 'chat']
// react-grid-layout uses integer grid units only.
// To get visual step ~0.5, we double columns and halve row height.
const GRID_COLS = 24
// Make vertical resize noticeably finer.
const GRID_ROW_HEIGHT = 0.5
const GRID_MARGIN: [number, number] = [6, 0]
const WIDGET_TITLES: Record<WidgetId, string> = {
  participants: 'Участники',
  pollsCreate: 'Новое голосование',
  pollsResults: 'Результаты голосований',
  expensesSummary: 'Общая сумма и долги',
  expensesCreate: 'Новая запись',
  expensesHistory: 'История трат',
  chat: 'Чат',
}
const WIDGET_ICONS: Record<WidgetId, string> = {
  participants: '👥',
  pollsCreate: '➕',
  pollsResults: '🗳️',
  expensesSummary: '💸',
  expensesCreate: '🧾',
  expensesHistory: '📚',
  chat: '💬',
}

export function TripDetail() {
  const { tripId } = useParams<{ tripId: string }>()
  const [trip, setTrip] = useState<Trip | null>(null)
  const [titleDraft, setTitleDraft] = useState('')
  const [destinationDraft, setDestinationDraft] = useState('')
  const [descriptionDraft, setDescriptionDraft] = useState('')
  const [startDateDraft, setStartDateDraft] = useState('')
  const [endDateDraft, setEndDateDraft] = useState('')
  const [editingTrip, setEditingTrip] = useState(false)
  const [tripSaving, setTripSaving] = useState(false)
  const [tripError, setTripError] = useState('')

  const defaultLayouts = useMemo<Layouts>(() => {
    const makeBase = (): RGLLayoutItem[] => [
      // Дефолт: сверху участники + чат, снизу бюджет + голосования. Размеры компактнее.
      { i: 'participants', x: 0, y: 0, w: 6, h: 2, minW: 2, minH: 1 },
      { i: 'chat', x: 6, y: 0, w: 5, h: 2, minW: 2, minH: 1 },
      { i: 'expensesSummary', x: 0, y: 6, w: 6, h: 2, minW: 2, minH: 1 },
      { i: 'expensesCreate', x: 0, y: 8, w: 6, h: 4, minW: 2, minH: 1 },
      { i: 'expensesHistory', x: 0, y: 12, w: 6, h: 2, minW: 2, minH: 1 },
      { i: 'pollsCreate', x: 6, y: 8, w: 5, h: 3, minW: 2, minH: 1 },
      { i: 'pollsResults', x: 6, y: 6, w: 5, h: 1, minW: 2, minH: 1 },
    ]
    return {
      lg: makeBase(),
      md: makeBase(),
      sm: makeBase(),
      xs: makeBase(),
      xxs: makeBase(),
    }
  }, [])

  const [layouts, setLayouts] = useState<Layouts>(defaultLayouts)
  const [collapsed, setCollapsed] = useState<Record<WidgetId, boolean>>({
    participants: false,
    pollsCreate: false,
    pollsResults: false,
    expensesSummary: false,
    expensesCreate: false,
    expensesHistory: false,
    chat: false,
  })
  const layoutLoadedRef = useRef(false)
  const saveTimerRef = useRef<number | null>(null)
  const latestLayoutsRef = useRef<Layouts>(defaultLayouts)
  const latestCollapsedRef = useRef<Record<WidgetId, boolean>>(collapsed)
  const [layoutStatus, setLayoutStatus] = useState<'loading' | 'ready' | 'saving' | 'saved' | 'error'>('loading')
  const ignoreLayoutChangeRef = useRef(true)
  const isInteractingRef = useRef(false)
  const activeBreakpointRef = useRef<string>('lg')
  const gridWrapRef = useRef<HTMLDivElement | null>(null)
  const [gridWidth, setGridWidth] = useState(0)
  const [, setDragArmed] = useState(false)

  useEffect(() => {
    const el = gridWrapRef.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      const w = Math.round(el.getBoundingClientRect().width)
      if (w > 0) setGridWidth(w)
    })
    ro.observe(el)
    // initial
    const w0 = Math.round(el.getBoundingClientRect().width)
    if (w0 > 0) setGridWidth(w0)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    function clearDragArm() {
      setDragArmed(false)
    }
    window.addEventListener('mouseup', clearDragArm)
    window.addEventListener('touchend', clearDragArm)
    return () => {
      window.removeEventListener('mouseup', clearDragArm)
      window.removeEventListener('touchend', clearDragArm)
    }
  }, [])

  function sanitizeLayouts(raw: any): Layouts | null {
    if (!raw || typeof raw !== 'object') return null
    const out: Layouts = {}
    for (const bp of ALL_BREAKPOINTS) {
      const items = (raw as any)[bp]
      if (!Array.isArray(items)) continue
      const prepared = items.filter((it: any) => it && typeof it === 'object')
      // Migrate only truly legacy layouts (old widget ids), not every "small" layout.
      const hasLegacyWidgetIds = prepared.some((it: any) => {
        const wid = String(it?.i || '')
        return wid === 'polls' || wid === 'expenses'
      })

      out[bp] = prepared
        .map((it: any) => {
          const num = (v: any, fallback: number) => {
            const n = typeof v === 'number' ? v : Number(v)
            return Number.isFinite(n) ? n : fallback
          }
          const scale = hasLegacyWidgetIds ? 2 : 1
          return {
            ...it,
            i:
              String(it.i) === 'polls' ? 'pollsResults'
                : String(it.i) === 'expenses' ? 'expensesHistory'
                  : String(it.i),
            x: num(it.x, 0) * scale,
            y: num(it.y, 0),
            w: Math.max(1, num(it.w, 2) * scale),
            h: Math.max(1, num(it.h, 6)),
            // Минимальный размер — действительно маленький (сброс старых ограничений из сохранённого JSON).
            // По горизонтали делаем минимум больше (≈x2)
            minW: 2,
            // По вертикали минимум оставляем минимальным, “визуальный” минимум регулируется rowHeight
            minH: 1,
            // Важно: не даём “залипнуть” в static/неперетаскиваемом состоянии из сохранённого JSON.
            static: false,
            // Перетаскивание разрешено только через drag-handle в заголовке.
            isDraggable: true,
            isResizable: true,
          } as RGLLayoutItem
        })
    }
    return Object.keys(out).length ? out : null
  }

  function fillMissingBreakpoints(from: Layouts): Layouts {
    const out: Layouts = { ...from }
    const base = (out.lg && out.lg.length > 0 ? out.lg : null) as RGLLayoutItem[] | null
    if (!base) return out
    for (const bp of ALL_BREAKPOINTS) {
      if (!Array.isArray(out[bp]) || out[bp].length === 0) out[bp] = base.map((it) => ({ ...it }))
    }
    return out
  }

  function clampLayoutItems(items: any[]): RGLLayoutItem[] {
    return (Array.isArray(items) ? items : []).map((it) => {
      const minW = Math.max(1, Number(it?.minW) || 1)
      const minH = Math.max(1, Number(it?.minH) || 1)
      const wRaw = Number(it?.w)
      const hRaw = Number(it?.h)
      const xRaw = Number(it?.x)
      const yRaw = Number(it?.y)

      const w = Number.isFinite(wRaw) ? Math.max(minW, Math.min(GRID_COLS, Math.round(wRaw))) : minW
      const h = Number.isFinite(hRaw) ? Math.max(minH, Math.round(hRaw)) : minH
      const maxX = Math.max(0, GRID_COLS - w)
      const x = Number.isFinite(xRaw) ? Math.max(0, Math.min(maxX, Math.round(xRaw))) : 0
      const y = Number.isFinite(yRaw) ? Math.max(0, Math.round(yRaw)) : 0

      return { ...it, x, y, w, h, minW, minH } as RGLLayoutItem
    })
  }

  function clampLayouts(layoutsRaw: Layouts): Layouts {
    const out: Layouts = {}
    for (const bp of ALL_BREAKPOINTS) out[bp] = clampLayoutItems((layoutsRaw as any)[bp] || [])
    return out
  }

  useEffect(() => {
    latestLayoutsRef.current = layouts
  }, [layouts])

  useEffect(() => {
    latestCollapsedRef.current = collapsed
  }, [collapsed])

  function scheduleSaveLayout(reason?: string) {
    if (!tripId) return
    if (!layoutLoadedRef.current) return
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current)
    setLayoutStatus('saving')
    saveTimerRef.current = window.setTimeout(() => {
      const payload = { layouts: latestLayoutsRef.current, collapsed: latestCollapsedRef.current }
      if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.info('[dashboard] save', {
          reason,
          tripId,
          activeBp: activeBreakpointRef.current,
          lg: (payload as any)?.layouts?.lg,
          collapsed: (payload as any)?.collapsed,
        })
      }
      saveTripDashboardLayout(tripId, payload)
        .then(() => setLayoutStatus('saved'))
        .catch((err) => {
          console.error('Failed to save dashboard layout', reason, err)
          setLayoutStatus('error')
        })
    }, 550)
  }

  function applyDashboardState(nextLayouts: Layouts, nextCollapsed: Record<WidgetId, boolean>, reason: string) {
    latestLayoutsRef.current = nextLayouts
    latestCollapsedRef.current = nextCollapsed
    setLayouts(nextLayouts)
    setCollapsed(nextCollapsed)
    scheduleSaveLayout(reason)
  }

  function withWidgetDefaultLayout(baseLayouts: Layouts, widget: WidgetId): Layouts {
    const baseLg = Array.isArray((baseLayouts as any).lg) ? [...(baseLayouts as any).lg] : []
    const def = defaultLayouts.lg.find((it) => it.i === widget)
    if (!def) return baseLayouts
    let replaced = false
    const nextLg = baseLg.map((it: any) => {
      if (String(it?.i) === widget) {
        replaced = true
        return { ...def }
      }
      return it
    })
    if (!replaced) nextLg.push({ ...def })
    return clampLayouts(fillMissingBreakpoints({ ...(baseLayouts as any), lg: nextLg } as any))
  }

  function toggleWidget(widget: WidgetId) {
    const currentCollapsed = latestCollapsedRef.current
    const openingNow = currentCollapsed[widget] === true
    const nextCollapsed = { ...currentCollapsed, [widget]: !currentCollapsed[widget] }
    const currentLayouts = latestLayoutsRef.current
    const nextLayouts = openingNow ? withWidgetDefaultLayout(currentLayouts, widget) : currentLayouts
    applyDashboardState(nextLayouts, nextCollapsed, openingNow ? 'open-widget-default' : 'collapse')
  }

  function openAllWidgets() {
    const nextCollapsed = {
      participants: false, pollsCreate: false, pollsResults: false,
      expensesSummary: false, expensesCreate: false, expensesHistory: false, chat: false,
    }
    const nextLayouts = clampLayouts(defaultLayouts)
    applyDashboardState(nextLayouts, nextCollapsed, 'open-all')
  }

  function resetDashboard() {
    const nextLayouts = clampLayouts(defaultLayouts)
    const nextCollapsed = {
      participants: false, pollsCreate: false, pollsResults: false,
      expensesSummary: false, expensesCreate: false, expensesHistory: false, chat: false,
    }
    applyDashboardState(nextLayouts, nextCollapsed, 'reset')
  }

  function blockDragFromNonHandle(e: React.MouseEvent | React.TouchEvent) {
    const target = e.target as HTMLElement | null
    if (!target) return
    if (target.closest('.dash-widget__drag-handle')) return
    // Не блокируем resize-ручку (правый нижний угол).
    if (target.closest('.react-resizable-handle')) return
    e.stopPropagation()
  }

  useEffect(() => {
    if (!tripId) return
    getTrip(tripId)
      .then(({ data }) => {
        setTrip(data)
        setTitleDraft(data.title)
        setDestinationDraft(data.destination || '')
        setDescriptionDraft(data.description || '')
        setStartDateDraft(data.start_date)
        setEndDateDraft(data.end_date)
      })
      .catch(() => setTrip(null))
  }, [tripId])

  useEffect(() => {
    if (!tripId) return
    layoutLoadedRef.current = false
    setLayoutStatus('loading')
    ignoreLayoutChangeRef.current = true
    ;(async () => {
      try {
        const { data } = await getTripDashboardLayout(tripId)
        if (import.meta.env.DEV) {
          // eslint-disable-next-line no-console
          console.info('[dashboard] load', { tripId, data, layoutsKeys: Object.keys((data as any)?.layouts || {}) })
        }
        const nextLayouts = data.layouts as Layouts | undefined
        if (nextLayouts && typeof nextLayouts === 'object') {
          // нормализуем: если пришли не все брейкпоинты — дополняем дефолтными
          const sanitized = sanitizeLayouts(nextLayouts)
          if (sanitized) {
            setLayouts(clampLayouts(fillMissingBreakpoints(sanitized)))
          } else {
            setLayouts(defaultLayouts)
          }
        }
        if (data.collapsed && typeof data.collapsed === 'object') {
          setCollapsed({
            participants: Boolean((data.collapsed as any).participants),
            pollsCreate: Boolean((data.collapsed as any).pollsCreate),
            pollsResults: Boolean((data.collapsed as any).pollsResults ?? (data.collapsed as any).polls),
            expensesSummary: Boolean((data.collapsed as any).expensesSummary),
            expensesCreate: Boolean((data.collapsed as any).expensesCreate),
            expensesHistory: Boolean((data.collapsed as any).expensesHistory ?? (data.collapsed as any).expenses),
            chat: Boolean((data.collapsed as any).chat),
          })
        }
      } catch {
        // если настроек нет/сервис недоступен — остаёмся на дефолте
      } finally {
        layoutLoadedRef.current = true
        setLayoutStatus('ready')
        // после первой отрисовки с загруженными layouts разрешаем onLayoutChange
        setTimeout(() => {
          ignoreLayoutChangeRef.current = false
        }, 0)
      }
    })()
  }, [tripId])

  function startEditTrip() {
    if (!trip) return
    setTitleDraft(trip.title)
    setDestinationDraft(trip.destination || '')
    setDescriptionDraft(trip.description || '')
    setStartDateDraft(trip.start_date)
    setEndDateDraft(trip.end_date)
    setTripError('')
    setEditingTrip(true)
  }

  function cancelEditTrip() {
    if (trip) {
      setTitleDraft(trip.title)
      setDestinationDraft(trip.destination || '')
      setDescriptionDraft(trip.description || '')
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
        description: descriptionDraft.trim() || null,
        start_date: startDateDraft,
        end_date: endDateDraft,
      })
      setTrip(data)
      setTitleDraft(data.title)
      setDestinationDraft(data.destination || '')
      setDescriptionDraft(data.description || '')
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
  const visibleWidgets: WidgetId[] = DASH_WIDGETS.filter((w) => !collapsed[w])
  const collapsedWidgets: WidgetId[] = DASH_WIDGETS.filter((w) => collapsed[w])
  const interactiveLayout = ((layouts as any).lg || [])
    .filter((it: any) => DASH_WIDGETS.includes((it?.i === 'polls' ? 'pollsResults' : it?.i) as WidgetId))
    .map((it: any) => ({
      ...it,
      i: it?.i === 'polls' ? 'pollsResults' : it?.i,
      isDraggable: true,
      isResizable: true,
      static: false,
    }))

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
                <label htmlFor="trip-description" className="board-edit-label">Описание</label>
                <textarea
                  id="trip-description"
                  className="board-title-input board-title-input--secondary"
                  value={descriptionDraft}
                  onChange={(e) => setDescriptionDraft(e.target.value)}
                  disabled={tripSaving}
                  placeholder="Кратко о плане поездки"
                  aria-label="Описание поездки"
                  rows={3}
                />
                <div className="board-title-actions">
                  <button type="button" className="btn btn-compact" onClick={saveTrip} disabled={tripSaving}>
                    {tripSaving ? 'Сохранение…' : 'Сохранить'}
                  </button>
                  <button type="button" className="btn btn-secondary btn-compact" onClick={cancelEditTrip} disabled={tripSaving}>
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

        <div className="trip-dashboard">
          <div className="trip-dashboard__bar">
            <div className="trip-dashboard__hint">
              Перетаскивайте окна и меняйте размер — раскладку можно настроить под себя.
              <span className={`trip-dashboard__status trip-dashboard__status--${layoutStatus}`}>
                {layoutStatus === 'loading' && 'Загружаю…'}
                {layoutStatus === 'ready' && 'Готово'}
                {layoutStatus === 'saving' && 'Сохраняю…'}
                {layoutStatus === 'saved' && 'Сохранено'}
                {layoutStatus === 'error' && 'Не удалось сохранить'}
              </span>
            </div>
            <div className="trip-dashboard__actions">
              <button type="button" className="btn btn-secondary btn-compact" onClick={resetDashboard}>
                Сбросить раскладку
              </button>
            </div>
          </div>

          <div className="trip-dashboard-layout">
            <div ref={gridWrapRef} className="trip-dashboard-layout__main">
            <DashboardGrid
              className="trip-dashboard__grid"
              width={gridWidth || 1200}
              cols={GRID_COLS}
              // Более мелкая сетка для плавного ресайза.
              rowHeight={GRID_ROW_HEIGHT}
              margin={GRID_MARGIN}
              containerPadding={[0, 0]}
              draggableHandle=".dash-widget__drag-handle"
              draggableCancel=":not(.dash-widget__drag-handle):not(.dash-widget__drag-handle *)"
              isDraggable={true}
              isResizable={true}
              resizeHandles={['se']}
              compactType={null as any}
              verticalCompact={false}
              isBounded={true}
              maxRows={999}
              layout={interactiveLayout}
            onDragStart={() => {
              isInteractingRef.current = true
            }}
            onResizeStart={() => {
              isInteractingRef.current = true
            }}
            onDragStop={(layout: any, oldItem: any) => {
              isInteractingRef.current = false
              setDragArmed(false)
              // Важно: фиксируем финальный layout из события dragStop (onLayoutChange может не успеть/не сработать)
              setLayouts((prev) => {
                const next: Layouts = fillMissingBreakpoints({
                  ...(prev as any),
                  lg: Array.isArray(layout) ? layout : (prev as any).lg,
                } as any)
                const sanitized = sanitizeLayouts(next) || next
                const clamped = clampLayouts(sanitized as Layouts)
                latestLayoutsRef.current = clamped
                return clamped
              })
              setTimeout(() => scheduleSaveLayout('drag'), 0)
              if (import.meta.env.DEV) {
                const moved = Array.isArray(layout)
                  ? layout.find((it: any) => String(it?.i) === String(oldItem?.i))
                  : null
                const movedX = moved ? moved.x : undefined
                // eslint-disable-next-line no-console
                console.info('[dashboard] dragStop item', { bp: 'lg', i: oldItem?.i, oldX: oldItem?.x, movedX, gridWidth })
              }
            }}
            onResizeStop={(layout: any, oldItem: any) => {
              isInteractingRef.current = false
              // Важно: фиксируем финальный layout из события resizeStop (onLayoutChange может не успеть/не сработать)
              setLayouts((prev) => {
                const next: Layouts = fillMissingBreakpoints({
                  ...(prev as any),
                  lg: Array.isArray(layout) ? layout : (prev as any).lg,
                } as any)
                const sanitized = sanitizeLayouts(next) || next
                const clamped = clampLayouts(sanitized as Layouts)
                latestLayoutsRef.current = clamped
                return clamped
              })
              setTimeout(() => scheduleSaveLayout('resize'), 0)
              if (import.meta.env.DEV) {
                const moved = Array.isArray(layout)
                  ? layout.find((it: any) => String(it?.i) === String(oldItem?.i))
                  : null
                const movedH = moved ? moved.h : undefined
                // eslint-disable-next-line no-console
                console.info('[dashboard] resizeStop item', { bp: 'lg', i: oldItem?.i, oldH: oldItem?.h, movedH })
              }
            }}
            onLayoutChange={(current: any) => {
              if (!layoutLoadedRef.current) return
              if (ignoreLayoutChangeRef.current) return
              // Важно: НЕ подхватываем автопересчёт при маунте/смене ширины.
              // Обновляем layouts только во время реального drag/resize.
              if (!isInteractingRef.current) return
              const next: Layouts = fillMissingBreakpoints({ lg: current } as any)
              const sanitized = sanitizeLayouts(next) || next
              const clamped = clampLayouts(sanitized as Layouts)
              latestLayoutsRef.current = clamped
              setLayouts(clamped)
            }}
            >
            {visibleWidgets.includes('participants') && (
            <section
              key="participants"
              className="dash-widget"
              onMouseDownCapture={blockDragFromNonHandle}
              onTouchStartCapture={blockDragFromNonHandle}
            >
              <div className="dash-widget__head">
                <span className="dash-widget__title">
                  <span
                    className="dash-widget__drag-handle"
                    title="Перетащить окно"
                    aria-hidden
                    onMouseDown={() => setDragArmed(true)}
                    onTouchStart={() => setDragArmed(true)}
                  >⋮⋮</span>
                  Участники
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-compact"
                  onClick={() => toggleWidget('participants')}
                  aria-label="Свернуть окно"
                  title="Свернуть"
                >
                  -
                </button>
              </div>
              <TripParticipants tripId={tripId} />
            </section>
            )}

            {visibleWidgets.includes('pollsCreate') && (
            <section
              key="pollsCreate"
              className="dash-widget"
              onMouseDownCapture={blockDragFromNonHandle}
              onTouchStartCapture={blockDragFromNonHandle}
            >
              <div className="dash-widget__head">
                <span className="dash-widget__title">
                  <span
                    className="dash-widget__drag-handle"
                    title="Перетащить окно"
                    aria-hidden
                    onMouseDown={() => setDragArmed(true)}
                    onTouchStart={() => setDragArmed(true)}
                  >⋮⋮</span>
                  Новое голосование
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-compact"
                  onClick={() => toggleWidget('pollsCreate')}
                  aria-label="Свернуть окно"
                  title="Свернуть"
                >
                  -
                </button>
              </div>
              <TripPollsCreate tripId={tripId} />
            </section>
            )}

            {visibleWidgets.includes('pollsResults') && (
            <section
              key="pollsResults"
              className="dash-widget"
              onMouseDownCapture={blockDragFromNonHandle}
              onTouchStartCapture={blockDragFromNonHandle}
            >
              <div className="dash-widget__head">
                <span className="dash-widget__title">
                  <span
                    className="dash-widget__drag-handle"
                    title="Перетащить окно"
                    aria-hidden
                    onMouseDown={() => setDragArmed(true)}
                    onTouchStart={() => setDragArmed(true)}
                  >⋮⋮</span>
                  Результаты голосований
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-compact"
                  onClick={() => toggleWidget('pollsResults')}
                  aria-label="Свернуть окно"
                  title="Свернуть"
                >
                  -
                </button>
              </div>
              <TripPollsResults tripId={tripId} />
            </section>
            )}

            {visibleWidgets.includes('expensesSummary') && (
            <section
              key="expensesSummary"
              className="dash-widget"
              onMouseDownCapture={blockDragFromNonHandle}
              onTouchStartCapture={blockDragFromNonHandle}
            >
              <div className="dash-widget__head">
                <span className="dash-widget__title">
                  <span
                    className="dash-widget__drag-handle"
                    title="Перетащить окно"
                    aria-hidden
                    onMouseDown={() => setDragArmed(true)}
                    onTouchStart={() => setDragArmed(true)}
                  >⋮⋮</span>
                  Общая сумма и долги
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-compact"
                  onClick={() => toggleWidget('expensesSummary')}
                  aria-label="Свернуть окно"
                  title="Свернуть"
                >
                  -
                </button>
              </div>
              <TripExpensesSummary tripId={tripId} />
            </section>
            )}

            {visibleWidgets.includes('expensesCreate') && (
            <section
              key="expensesCreate"
              className="dash-widget"
              onMouseDownCapture={blockDragFromNonHandle}
              onTouchStartCapture={blockDragFromNonHandle}
            >
              <div className="dash-widget__head">
                <span className="dash-widget__title">
                  <span
                    className="dash-widget__drag-handle"
                    title="Перетащить окно"
                    aria-hidden
                    onMouseDown={() => setDragArmed(true)}
                    onTouchStart={() => setDragArmed(true)}
                  >⋮⋮</span>
                  Новая запись
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-compact"
                  onClick={() => toggleWidget('expensesCreate')}
                  aria-label="Свернуть окно"
                  title="Свернуть"
                >
                  -
                </button>
              </div>
              <TripExpensesCreate tripId={tripId} />
            </section>
            )}

            {visibleWidgets.includes('expensesHistory') && (
            <section
              key="expensesHistory"
              className="dash-widget"
              onMouseDownCapture={blockDragFromNonHandle}
              onTouchStartCapture={blockDragFromNonHandle}
            >
              <div className="dash-widget__head">
                <span className="dash-widget__title">
                  <span
                    className="dash-widget__drag-handle"
                    title="Перетащить окно"
                    aria-hidden
                    onMouseDown={() => setDragArmed(true)}
                    onTouchStart={() => setDragArmed(true)}
                  >⋮⋮</span>
                  История трат
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-compact"
                  onClick={() => toggleWidget('expensesHistory')}
                  aria-label="Свернуть окно"
                  title="Свернуть"
                >
                  -
                </button>
              </div>
              <TripExpensesHistory tripId={tripId} />
            </section>
            )}

            {visibleWidgets.includes('chat') && (
            <section
              key="chat"
              className="dash-widget"
              onMouseDownCapture={blockDragFromNonHandle}
              onTouchStartCapture={blockDragFromNonHandle}
            >
              <div className="dash-widget__head">
                <span className="dash-widget__title">
                  <span
                    className="dash-widget__drag-handle"
                    title="Перетащить окно"
                    aria-hidden
                    onMouseDown={() => setDragArmed(true)}
                    onTouchStart={() => setDragArmed(true)}
                  >⋮⋮</span>
                  Чат
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-compact"
                  onClick={() => toggleWidget('chat')}
                  aria-label="Свернуть окно"
                  title="Свернуть"
                >
                  -
                </button>
              </div>
              <TripChat tripId={tripId} />
            </section>
            )}
            </DashboardGrid>
            </div>

            <aside className="trip-dashboard-collapsed">
              <div className="trip-dashboard-collapsed__head">
                <h3 className="trip-dashboard-collapsed__title">Свернутые окна ({collapsedWidgets.length})</h3>
                {collapsedWidgets.length > 0 && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-compact trip-dashboard-collapsed__open-all"
                    onClick={openAllWidgets}
                  >
                    Открыть все
                  </button>
                )}
              </div>
              {collapsedWidgets.length > 0 ? (
                <div className="trip-dashboard-collapsed__list">
                  {collapsedWidgets.map((wid) => (
                    <div key={wid} className="trip-dashboard-collapsed__item">
                      <span className="trip-dashboard-collapsed__item-label">
                        <span className="trip-dashboard-collapsed__icon" aria-hidden>{WIDGET_ICONS[wid]}</span>
                        <span>{WIDGET_TITLES[wid]}</span>
                      </span>
                      <button
                        type="button"
                        className="btn btn-secondary btn-compact"
                        onClick={() => toggleWidget(wid)}
                      >
                        Открыть
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="trip-dashboard-collapsed__empty">
                  Здесь будут свернутые окна.
                </p>
              )}
            </aside>
          </div>
        </div>
      </div>
    </div>
  )
}
