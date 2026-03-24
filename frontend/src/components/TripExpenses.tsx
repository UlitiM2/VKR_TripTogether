import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { getExpenses, addExpense, getDebts, deleteExpense, type Expense, type DebtItem } from '../api/expenses'
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

export function TripExpenses({ tripId }: { tripId: string }) {
  const { user } = useAuth()
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [debts, setDebts] = useState<DebtItem[]>([])
  const [participants, setParticipants] = useState<Participant[]>([])
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [paidByUserId, setPaidByUserId] = useState('')
  const [splitBetween, setSplitBetween] = useState<string[]>([])
  const [names, setNames] = useState<Record<string, string>>({})
  const [showAllExpenses, setShowAllExpenses] = useState(false)
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const [ex, dt, pp] = await Promise.all([
        getExpenses(tripId),
        getDebts(tripId),
        getParticipants(tripId),
      ])
      setExpenses(ex.data)
      setDebts(dt.data.debts)
      setParticipants(pp.data)
      if (!paidByUserId && user?.id) {
        setPaidByUserId(user.id)
      }
      if (splitBetween.length === 0 && pp.data.length > 0 && user?.id) {
        const me = pp.data.find((p) => p.user_id === user.id)
        if (me) setSplitBetween([user.id])
      }
    } catch {
      setExpenses([])
      setDebts([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [tripId])

  useEffect(() => {
    const ids = new Set<string>()
    participants.forEach((p) => ids.add(p.user_id))
    expenses.forEach((e) => ids.add(e.paid_by_user_id))
    debts.forEach((d) => {
      ids.add(d.from_user_id)
      ids.add(d.to_user_id)
    })
    const listIds = Array.from(ids)
    if (listIds.length === 0) {
      setNames({})
      return
    }
    Promise.all(
      listIds.map(async (id) => {
        try {
          const { data } = await getUserProfile(id)
          const name = data.full_name?.trim() || data.username?.trim() || data.email?.trim() || shortId(id)
          return [id, name] as const
        } catch {
          return [id, shortId(id)] as const
        }
      }),
    ).then((pairs) => {
      setNames(Object.fromEntries(pairs))
    })
  }, [participants, expenses, debts])

  const totalAmount = expenses.reduce((sum, ex) => sum + ex.amount, 0)
  const visibleExpenses = showAllExpenses ? expenses : expenses.slice(0, 3)
  const hiddenCount = Math.max(0, expenses.length - 3)

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
      load()
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

  async function handleDeleteExpense(expenseId: string) {
    if (!confirm('Удалить эту трату?')) return
    try {
      await deleteExpense(tripId, expenseId)
      load()
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) return <div className="loading">Загрузка...</div>

  return (
    <div className="card board-widget board-widget--money">
      <h2>Расходы</h2>

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

      <ul className="expense-list-simple">
        {visibleExpenses.map((ex) => (
          <li key={ex.id} className="expense-item-simple">
            <div className="expense-item-simple__main">
              <span className="expense-item-simple__amount">{formatMoney(ex.amount)}</span>
              <span className="expense-item-simple__payer">{names[ex.paid_by_user_id] || shortId(ex.paid_by_user_id)}</span>
              {ex.category && <span className="expense-item-simple__tag">{ex.category}</span>}
              {ex.description ? <span className="expense-item-simple__desc">{ex.description}</span> : <span className="expense-item-simple__desc muted">Без описания</span>}
            </div>
            {user?.id === ex.paid_by_user_id && (
              <button type="button" className="btn btn-danger btn-compact" onClick={() => handleDeleteExpense(ex.id)}>
                ✕
              </button>
            )}
          </li>
        ))}
      </ul>
      {hiddenCount > 0 && (
        <button type="button" className="btn btn-secondary btn-compact" onClick={() => setShowAllExpenses((v) => !v)}>
          {showAllExpenses ? 'Свернуть' : `Показать ещё ${hiddenCount}`}
        </button>
      )}
    </div>
  )
}
