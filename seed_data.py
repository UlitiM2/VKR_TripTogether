
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/tripplanner",
)


@dataclass(frozen=True)
class SeedUser:
    email: str
    username: str
    full_name: str
    password: str
    avatar_url: str | None = None


def stable_uuid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"triptogether-seed:{name}")


def make_password_hash(password: str) -> str:
    try:
        import bcrypt  
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency 'bcrypt'. Run: py -m pip install bcrypt "
            "or execute seed_data.py from auth-service .venv where deps are installed."
        ) from exc
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def upsert_user(session: Session, u: SeedUser) -> uuid.UUID:
    user_id = stable_uuid(u.email)
    hashed_password = make_password_hash(u.password)
    session.execute(
        text(
            """
            INSERT INTO users (id, email, username, full_name, avatar_url, hashed_password, is_active, is_verified, created_at, updated_at)
            VALUES (:id, :email, :username, :full_name, :avatar_url, :hashed_password, true, false, now(), now())
            ON CONFLICT (email) DO UPDATE SET
              username = EXCLUDED.username,
              full_name = EXCLUDED.full_name,
              avatar_url = EXCLUDED.avatar_url,
              hashed_password = EXCLUDED.hashed_password,
              is_active = true,
              created_at = COALESCE(users.created_at, now()),
              updated_at = now()
            """
        ),
        {
            "id": str(user_id),
            "email": u.email,
            "username": u.username,
            "full_name": u.full_name,
            "avatar_url": u.avatar_url,
            "hashed_password": hashed_password,
        },
    )
    return user_id


def upsert_trip(session: Session, *, trip_id: uuid.UUID, title: str, destination: str, start: date, end: date, description: str, created_by: uuid.UUID) -> uuid.UUID:
    session.execute(
        text(
            """
            INSERT INTO trips (id, title, destination, start_date, end_date, description, created_by)
            VALUES (:id, :title, :destination, :start_date, :end_date, :description, :created_by)
            ON CONFLICT (id) DO UPDATE SET
              title = EXCLUDED.title,
              destination = EXCLUDED.destination,
              start_date = EXCLUDED.start_date,
              end_date = EXCLUDED.end_date,
              description = EXCLUDED.description,
              created_by = EXCLUDED.created_by
            """
        ),
        {
            "id": str(trip_id),
            "title": title,
            "destination": destination,
            "start_date": start,
            "end_date": end,
            "description": description,
            "created_by": str(created_by),
        },
    )
    return trip_id


def ensure_participant(session: Session, *, trip_id: uuid.UUID, user_id: uuid.UUID, role: str, accepted: bool) -> None:
    participant_id = stable_uuid(f"{trip_id}:{user_id}")
    session.execute(
        text(
            """
            INSERT INTO trip_participants (id, trip_id, user_id, role, accepted_at)
            VALUES (:id, :trip_id, :user_id, :role, CASE WHEN :accepted THEN now() ELSE NULL END)
            ON CONFLICT (id) DO UPDATE SET
              role = EXCLUDED.role,
              accepted_at = EXCLUDED.accepted_at
            """
        ),
        {
            "id": str(participant_id),
            "trip_id": str(trip_id),
            "user_id": str(user_id),
            "role": role,
            "accepted": accepted,
        },
    )


def main() -> None:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    users = [
        SeedUser("maria@example.com", "maria", "Мария Улитина", "password123", "https://i.pravatar.cc/150?img=5"),
        SeedUser("masha@example.com", "masha", "Машутка Улитина", "password123", "https://i.pravatar.cc/150?img=32"),
        SeedUser("ivan@example.com", "ivan", "Иван Петров", "password123", "https://i.pravatar.cc/150?img=12"),
        SeedUser("olga@example.com", "olga", "Ольга Соколова", "password123", "https://i.pravatar.cc/150?img=47"),
        SeedUser("dima@example.com", "dima", "Дмитрий Кузнецов", "password123", "https://i.pravatar.cc/150?img=18"),
    ]

    with Session(engine) as session:
        user_ids: dict[str, uuid.UUID] = {}
        for u in users:
            user_ids[u.email] = upsert_user(session, u)

        trip1_id = stable_uuid("trip:spb-weekend")
        trip2_id = stable_uuid("trip:moscow-work")

        upsert_trip(
            session,
            trip_id=trip1_id,
            title="Питер на выходные",
            destination="Санкт‑Петербург",
            start=date(2026, 5, 2),
            end=date(2026, 5, 4),
            description="Едем гулять, музеи, кофе и немного дождя.",
            created_by=user_ids["maria@example.com"],
        )
        upsert_trip(
            session,
            trip_id=trip2_id,
            title="Москва: встреча команды",
            destination="Москва",
            start=date(2026, 6, 12),
            end=date(2026, 6, 15),
            description="Рабочая поездка + совместный ужин.",
            created_by=user_ids["ivan@example.com"],
        )

        ensure_participant(session, trip_id=trip1_id, user_id=user_ids["maria@example.com"], role="organizer", accepted=True)
        ensure_participant(session, trip_id=trip1_id, user_id=user_ids["masha@example.com"], role="member", accepted=True)
        ensure_participant(session, trip_id=trip1_id, user_id=user_ids["olga@example.com"], role="member", accepted=True)

        ensure_participant(session, trip_id=trip2_id, user_id=user_ids["ivan@example.com"], role="organizer", accepted=True)
        ensure_participant(session, trip_id=trip2_id, user_id=user_ids["dima@example.com"], role="member", accepted=True)
        ensure_participant(session, trip_id=trip2_id, user_id=user_ids["maria@example.com"], role="member", accepted=True)

        session.commit()

    print("Seed completed.")
    print("Users/password: password123")
    print("Example login: maria@example.com / password123")


if __name__ == "__main__":
    main()

