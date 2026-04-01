import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { getExpenses, addExpense, getDebts, deleteExpense, getExpenseSplitBetween, type Expense, type DebtItem } from '../api/expenses'
import { getParticipants, type Participant } from '../api/participants'
import { getUserProfile } from '../api/user'

function formatMoney(n: number) {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: Number.isInteger(n) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(n)
}

function shortId(id: string) {
  return id.length > 10 ? `${id.slice(0, 8)}…` : id
}

const EXPENSES_UPDATED_EVENT = 'trip-expenses-updated'

function notifyExpensesUpdated(tripId: string) {
  window.dispatchEvent(new CustomEvent(EXPENSES_UPDATED_EVENT, { detail: { tripId } }))
}

async function loadNames(ids: string[]): Promise<Record<string, string>> {
  const uniq = Array.from(new Set(ids))
  const pairs = await Promise.all(
    uniq.map(async (id) => {
      try {
        const { data } = await getUserProfile(id)
        const name = data.full_name?.trim() || data.username?.trim() || data.email?.trim() || shortId(id)
        return [id, name] as const
      } catch {
        return [id, shortId(id)] as const
      }
    }),
  )
  return Object.fromEntries(pairs)
}

export function TripExpensesSummary({ tripId }: { tripId: string }) {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [debts, setDebts] = useState<DebtItem[]>([])
  const [names, setNames] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const [ex, dt] = await Promise.all([getExpenses(tripId), getDebts(tripId)])
      setExpenses(ex.data)
      setDebts(dt.data.debts)
      const ids = [
        ...ex.data.map((e) => e.paid_by_user_id),
        ...dt.data.debts.flatMap((d) => [d.from_user_id, d.to_user_id]),
      ]
      setNames(await loadNames(ids))
    } catch {
      setExpenses([])
      setDebts([])
      setNames({})
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
    window.addEventListener(EXPENSES_UPDATED_EVENT, onUpdated)
    return () => window.removeEventListener(EXPENSES_UPDATED_EVENT, onUpdated)
  }, [tripId])

  if (loading) return <div className="loading">Загрузка...</div>

  const totalAmount = expenses.reduce((sum, ex) => sum + ex.amount, 0)

  return (
    <div className="card board-widget board-widget--money">
      <div className="expense-total card">
        <span className="expense-total__label">Общая сумма поездки</span>
        <strong className="expense-total__value">{formatMoney(totalAmount)}</strong>
      </div>
      <h3 className="expense-subtitle">Кто кому должен</h3>
      {debts.length === 0 ? (
        <p className="widget-hint">Нет долгов</p>
      ) : (
        <ul className="debt-list-simple">
          {debts.map((d, i) => (
            <li key={i} className="debt-item-simple">
              {names[d.from_user_id] || shortId(d.from_user_id)} → {names[d.to_user_id] || shortId(d.to_user_id)}: {formatMoney(d.amount)}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function TripExpensesCreate({ tripId }: { tripId: string }) {
  const { user } = useAuth()
  const [participants, setParticipants] = useState<Participant[]>([])
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [paidByUserId, setPaidByUserId] = useState('')
  const [splitBetween, setSplitBetween] = useState<string[]>([])
  const [names, setNames] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const { data } = await getParticipants(tripId)
      const pp = { data }
      setParticipants(pp.data)
      setNames(await loadNames(pp.data.map((p) => p.user_id)))
      if (!paidByUserId && user?.id) {
        setPaidByUserId(user.id)
      }
      if (splitBetween.length === 0 && pp.data.length > 0 && user?.id) {
        const me = pp.data.find((p) => p.user_id === user.id)
        if (me) setSplitBetween([user.id])
      }
    } catch {
      setParticipants([])
      setNames({})
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [tripId])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    const num = parseFloat(amount)
    if (isNaN(num) || num <= 0 || splitBetween.length === 0) return
    try {
      await addExpense(tripId, {
        amount: num,
        paid_by_user_id: paidByUserId || undefined,
        category: category || undefined,
        description: description || undefined,
        split_between: splitBetween,
      })
      setAmount('')
      setCategory('')
      setDescription('')
      if (user?.id) setPaidByUserId(user.id)
      notifyExpensesUpdated(tripId)
    } catch (err) {
      console.error(err)
    }
  }

  function toggleUser(uid: string) {
    setSplitBetween((prev) =>
      prev.includes(uid) ? prev.filter((id) => id !== uid) : [...prev, uid]
    )
  }

  function selectAllParticipants() {
    setSplitBetween(participants.map((p) => p.user_id))
  }

  function clearSplitBetween() {
    setSplitBetween([])
  }

  if (loading) return <div className="loading">Загрузка...</div>

  return (
    <div className="card board-widget board-widget--money">
      <form className="board-widget__form" onSubmit={handleAdd}>
        <label>Сумма</label>
        <input type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        <label>Категория</label>
        <input value={category} onChange={(e) => setCategory(e.target.value)} />
        <label>Кто оплатил</label>
        <select value={paidByUserId} onChange={(e) => setPaidByUserId(e.target.value)} required>
          <option value="" disabled>Выберите участника</option>
          {participants.map((p) => (
            <option key={p.user_id} value={p.user_id}>
              {names[p.user_id] || shortId(p.user_id)}
            </option>
          ))}
        </select>
        <label>Описание</label>
        <input value={description} onChange={(e) => setDescription(e.target.value)} />
        <label>Делить между</label>
        {participants.length > 0 && (
          <div className="split-actions-simple">
            <button type="button" className="split-action-btn" onClick={selectAllParticipants}>
              Выбрать всех
            </button>
            <button type="button" className="split-action-btn" onClick={clearSplitBetween}>
              Очистить
            </button>
          </div>
        )}
        <div className="split-checklist-simple">
          {participants.map((p) => (
            <label key={p.user_id} className="split-check-simple">
              <input
                type="checkbox"
                checked={splitBetween.includes(p.user_id)}
                onChange={() => toggleUser(p.user_id)}
              />
              <span>{names[p.user_id] || shortId(p.user_id)}</span>
            </label>
          ))}
        </div>
        <button type="submit">Добавить расход</button>
      </form>
    </div>
  )
}

export function TripExpensesHistory({ tripId }: { tripId: string }) {
  const { user } = useAuth()
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [splitBetweenByExpenseId, setSplitBetweenByExpenseId] = useState<Record<string, string[]>>({})
  const [names, setNames] = useState<Record<string, string>>({})
  const [showAllExpenses, setShowAllExpenses] = useState(false)
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const { data } = await getExpenses(tripId)
      setExpenses(data)
      setNames(await loadNames(data.map((e) => e.paid_by_user_id)))
    } catch {
      setExpenses([])
      setNames({})
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [tripId])

  useEffect(() => {
    if (expenses.length === 0) {
      setSplitBetweenByExpenseId({})
      return
    }
    let cancelled = false
    async function fetchSplits() {
      try {
        const pairs = await Promise.all(
          expenses.map(async (expense) => {
            const { data } = await getExpenseSplitBetween(tripId, expense.id)
            return [expense.id, data.user_ids] as const
          }),
        )
        const ids = pairs.flatMap(([, userIds]) => userIds)
        if (!cancelled) {
          setSplitBetweenByExpenseId(Object.fromEntries(pairs))
          const splitNames = await loadNames(ids)
          setNames((prev) => ({ ...prev, ...splitNames }))
        }
      } catch {
        // optional split tooltip
      }
    }
    fetchSplits()
    return () => {
      cancelled = true
    }
  }, [tripId, expenses])

  useEffect(() => {
    function onUpdated(e: Event) {
      const ce = e as CustomEvent<{ tripId?: string }>
      if (ce.detail?.tripId === tripId) load()
    }
    window.addEventListener(EXPENSES_UPDATED_EVENT, onUpdated)
    return () => window.removeEventListener(EXPENSES_UPDATED_EVENT, onUpdated)
  }, [tripId])

  async function handleDeleteExpense(expenseId: string) {
    if (!confirm('Удалить эту трату?')) return
    try {
      await deleteExpense(tripId, expenseId)
      notifyExpensesUpdated(tripId)
      load()
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) return <div className="loading">Загрузка...</div>

  const visibleExpenses = showAllExpenses ? expenses : expenses.slice(0, 3)
  const hiddenCount = Math.max(0, expenses.length - 3)

  return (
    <div className="card board-widget board-widget--money">
      <section className="expense-history">
        {hiddenCount > 0 && (
          <div className="expense-history-top-actions">
            <button
              type="button"
              className="btn btn-secondary btn-compact expense-show-more-btn"
              onClick={() => setShowAllExpenses((v) => !v)}
            >
              {showAllExpenses ? 'Свернуть' : `Показать ещё ${hiddenCount}`}
            </button>
          </div>
        )}

        <div className="expense-history-table" role="table" aria-label="История трат">
          <div className="expense-history-table__head" role="row">
            <div className="expense-history-table__cell">Кто оплатил</div>
            <div className="expense-history-table__cell">Делить между</div>
            <div className="expense-history-table__cell">Категория</div>
            <div className="expense-history-table__cell">Цена</div>
            <div className="expense-history-table__cell">Описание</div>
            <div className="expense-history-table__cell" />
          </div>
          <div className="expense-history-table__body">
            {visibleExpenses.map((ex) => (
              <div key={ex.id} className="expense-history-table__row">
                <div className="expense-history-table__cell expense-history-table__payer">
                  {names[ex.paid_by_user_id] || shortId(ex.paid_by_user_id)}
                </div>
                <div className="expense-history-table__cell expense-history-table__split">
                  {(() => {
                    const splitIds = splitBetweenByExpenseId[ex.id] || []
                    const tooltipNames =
                      splitIds.length > 0
                        ? splitIds.map((uid) => names[uid] || shortId(uid)).join(', ')
                        : ''
                    const label = ex.share_count ? `${ex.share_count} чел.` : '—'
                    return (
                      <span className="expense-split-tooltip" data-tooltip={tooltipNames || label} aria-label="Делить между">
                        {label}
                      </span>
                    )
                  })()}
                </div>
                <div className="expense-history-table__cell expense-history-table__category">{ex.category || '—'}</div>
                <div className="expense-history-table__cell expense-history-table__amount">{formatMoney(ex.amount)}</div>
                <div className="expense-history-table__cell expense-history-table__desc">{ex.description || 'Без описания'}</div>
                <div className="expense-history-table__cell expense-history-table__actions">
                  {user?.id === ex.paid_by_user_id && (
                    <button
                      type="button"
                      className="btn btn-danger btn-compact"
                      onClick={() => handleDeleteExpense(ex.id)}
                      aria-label="Удалить расход"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
