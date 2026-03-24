# TripTogether — Frontend

SPA на React + Vite + TypeScript. Вход, регистрация, поездки, участники, голосования, бюджет, чат (в т.ч. WebSocket).

## Требования

- Node.js 18+
- Запущенные backend-сервисы (auth 8001, user 8002, trip 8003, voting 8004, budget 8005, chat 8006)

## Установка и запуск

```bash
cd frontend
npm install
npm run dev
```

Приложение откроется на http://localhost:5173.

Vite проксирует запросы к API:
- `/api/auth` → localhost:8001
- `/api/user` → 8002
- `/api/trip` → 8003
- `/api/voting` → 8004
- `/api/budget` → 8005
- `/api/chat` → 8006 (включая WebSocket для чата)

## Сборка

```bash
npm run build
```

Статика в `dist/`. Для продакшена нужно настроить обратный прокси (nginx и т.п.) на бэкенд по путям `/api/*`.

## Структура

- `src/api/` — клиенты к backend (auth, trips, participants, polls, expenses, chat)
- `src/components/` — Layout, вкладки поездки (участники, голосования, бюджет, чат)
- `src/context/` — AuthContext (токен, пользователь)
- `src/pages/` — Login, Register, Trips, TripDetail, Profile
