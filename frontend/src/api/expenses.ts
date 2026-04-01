import { apiBudget } from './client'

export interface Expense {
  id: string
  trip_id: string
  paid_by_user_id: string
  amount: number
  category: string | null
  description: string | null
  created_at: string
  share_count: number
}

export interface DebtItem {
  from_user_id: string
  to_user_id: string
  amount: number
}

export interface ExpenseSplitResponse {
  user_ids: string[]
}

export interface DebtsSummary {
  debts: DebtItem[]
}

export function getExpenses(tripId: string) {
  return apiBudget.get<Expense[]>(`/trips/${tripId}/expenses`)
}

export function addExpense(
  tripId: string,
  data: { amount: number; category?: string; description?: string; split_between: string[]; paid_by_user_id?: string }
) {
  return apiBudget.post<Expense>(`/trips/${tripId}/expenses`, data)
}

export function getDebts(tripId: string) {
  return apiBudget.get<DebtsSummary>(`/trips/${tripId}/expenses/debts`)
}

export function deleteExpense(tripId: string, expenseId: string) {
  return apiBudget.delete(`/trips/${tripId}/expenses/${expenseId}`)
}

export function getExpenseSplitBetween(tripId: string, expenseId: string) {
  return apiBudget.get<ExpenseSplitResponse>(`/trips/${tripId}/expenses/${expenseId}/split`)
}
