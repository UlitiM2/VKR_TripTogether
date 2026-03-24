# Тесты TripTogether

## Требования

- Python 3.11+
- PostgreSQL (для тестов используется БД из `DATABASE_URL` / `TEST_DATABASE_URL`)
- Установить зависимости сервиса, который тестируем, и pytest:

```bash
pip install pytest httpx
cd trip-service && pip install -r requirements.txt
cd ../voting-service && pip install -r requirements.txt
```

Либо из корня (тогда оба сервиса должны быть в PYTHONPATH при запуске — см. ниже).

## Запуск

Тесты разделены по сервисам. **Запускать нужно по отдельности**, так как у каждого сервиса свой конфиг и свои подмены зависимостей.

### Trip-service (поездки и участники)

Поднять PostgreSQL (например: `docker-compose up -d postgres`). При необходимости задать БД.

**PowerShell** (из папки `trip-service`):

```powershell
cd trip-service
$env:PYTHONPATH = (Get-Location).Path
py -m pytest ..\tests\trip_service -v
```

**Bash / Linux / macOS**:

```bash
cd trip-service
PYTHONPATH=. pytest ../tests/trip_service -v
```

### Voting-service (голосования)

Та же БД (должна быть доступна таблица `trips`).

**PowerShell** (из папки `voting-service`):

```powershell
cd voting-service
$env:PYTHONPATH = (Get-Location).Path + ";..\trip-service"
py -m pytest ..\tests\voting_service -v
```

**Bash**:

```bash
cd voting-service
PYTHONPATH=.:../trip-service pytest ../tests/voting_service -v
```

### Budget-service (бюджет и расходы)

**PowerShell** (из папки `budget-service`):

```powershell
cd budget-service
$env:PYTHONPATH = (Get-Location).Path + ";..\trip-service"
py -m pytest ..\tests\budget_service -v
```

**Bash**:

```bash
cd budget-service
PYTHONPATH=.:../trip-service pytest ../tests/budget_service -v
```

## Структура

- `tests/trip_service/` — тесты trip-service (trips, participants)
- `tests/voting_service/` — тесты voting-service (polls, options, vote)
- `tests/budget_service/` — тесты budget-service (expenses, debts)
- В каждом `conftest.py` подменяются `get_db`, `verify_token`, при необходимости `check_trip_access`; используется одна сессия с откатом после теста.
