import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const HERO_IMG = '/home-hero.jpeg'

export function Home() {
  const { token } = useAuth()

  return (
    <div className="home-page">
      <section className="home-landing" aria-labelledby="home-landing-title">
        <div className="home-landing__left">
          <h1 id="home-landing-title" className="home-landing__title">
            TripTogether
          </h1>
          <p className="home-landing__tagline">
            Одно место для дат, голосований, бюджета и договорённостей вашей компании.
          </p>
          <p className="home-landing__desc">
            Когда едете не один, важно не терять нити: кто за что платил, куда всем удобнее, что
            выбрать из вариантов. Сервис помогает держать поездку в одном пространстве — от идей до
            решений.
          </p>

          <div className="home-spotlights" role="group" aria-label="Быстрый доступ к разделам">
            <article className="home-spotlight">
              <div className="home-spotlight__thumb" aria-hidden>
                <img
                  className="home-spotlight__img"
                  src="/home-previews/board.png"
                  alt=""
                  loading="lazy"
                />
              </div>
              <span className="home-spotlight__badge">Голосования</span>
              <h3 className="home-spotlight__name">Результаты голосований</h3>
              <p className="home-spotlight__text home-spotlight__text--last">
                Сводка выборов группы: куда едем, даты и другие решения наглядно.
              </p>
            </article>
            <article className="home-spotlight">
              <div className="home-spotlight__thumb home-spotlight__thumb--map" aria-hidden>
                <img
                  className="home-spotlight__img"
                  src="/home-previews/map.png"
                  alt=""
                  loading="lazy"
                />
              </div>
              <span className="home-spotlight__badge home-spotlight__badge--soft">Карта</span>
              <h3 className="home-spotlight__name">Поездки на карте</h3>
              <p className="home-spotlight__text home-spotlight__text--last">
                Отмечайте направления и создавайте поездку с подсказкой.
              </p>
            </article>
          </div>

          <div className="home-landing__cta-row">
            <Link to="/trips" className="home-landing__primary-cta">
              Перейти к моим поездкам
              <span className="home-landing__primary-cta-arrow" aria-hidden>
                →
              </span>
            </Link>
            {token ? (
              <Link to="/profile" className="home-landing__ghost-cta">
                Профиль
              </Link>
            ) : (
              <Link to="/register" className="home-landing__ghost-cta">
                Создать аккаунт
              </Link>
            )}
          </div>
        </div>

        <div className="home-landing__visual">
          <div className="home-landing__visual-inner">
            <img
              className="home-landing__hero-img"
              src={HERO_IMG}
              alt="Путешествие: блокнот и карта на столе"
            />
          </div>
        </div>
      </section>

      <section className="home-features-section" aria-labelledby="home-features-title">
        <header className="home-features-section__head">
          <h2 id="home-features-title" className="home-features-section__title">
            Возможности
          </h2>
          <p className="home-features-section__lead">
            Всё для совместной поездки — даты, решения группы, учёт трат и общение на одной доске.
          </p>
        </header>
        <ul className="home-features">
          <li className="home-feature home-feature--trips">
            <span className="home-feature__icon-wrap" aria-hidden>
              <span className="home-feature__icon">🗓️</span>
            </span>
            <h3 className="home-feature__name">Поездки</h3>
            <p className="home-feature__desc">
              Создавайте поездки, приглашайте участников и держите договорённости в одном месте.
            </p>
          </li>
          <li className="home-feature home-feature--polls">
            <span className="home-feature__icon-wrap" aria-hidden>
              <span className="home-feature__icon">🗳️</span>
            </span>
            <h3 className="home-feature__name">Голосования</h3>
            <p className="home-feature__desc">
              Собирайте мнение группы и фиксируйте выбранные варианты без хаоса в чатах.
            </p>
          </li>
          <li className="home-feature home-feature--budget">
            <span className="home-feature__icon-wrap" aria-hidden>
              <span className="home-feature__icon">💰</span>
            </span>
            <h3 className="home-feature__name">Бюджет</h3>
            <p className="home-feature__desc">
              Учитывайте общие траты и смотрите понятную схему «кто кому должен».
            </p>
          </li>
          <li className="home-feature home-feature--chat">
            <span className="home-feature__icon-wrap" aria-hidden>
              <span className="home-feature__icon">💬</span>
            </span>
            <h3 className="home-feature__name">Чат</h3>
            <p className="home-feature__desc">
              Обсуждайте планы в чате каждой поездки рядом с опросами и расходами.
            </p>
          </li>
        </ul>
      </section>

      <section className="home-section home-section--cta home-section--soft">
        <h2 className="home-section__title">Готовы начать?</h2>
        <p className="home-section__text home-section__text--center">
          Создайте поездку, пригласите друзей и попробуйте совместное планирование в действии.
        </p>
        <div className="home-cta-footer">
          <Link to="/trips" className="home-landing__primary-cta">
            Открыть поездки
            <span className="home-landing__primary-cta-arrow" aria-hidden>
              →
            </span>
          </Link>
          {!token && (
            <Link to="/register" className="home-landing__ghost-cta">
              Зарегистрироваться
            </Link>
          )}
        </div>
      </section>
    </div>
  )
}
