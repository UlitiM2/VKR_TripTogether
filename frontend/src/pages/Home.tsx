import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function Home() {
  const { token } = useAuth()

  return (
    <div className="home-page">
      <section className="home-hero">
        <h1 className="home-hero__title">TripTogether</h1>
        <p className="home-hero__lead">
          Веб-сервис для совместного планирования групповых поездок: одно место для дат,
          голосований, бюджета и общения вашей компании.
        </p>
        <div className="home-hero__actions">
          <Link to="/trips" className="btn home-hero__cta">
            Перейти к моим поездкам
          </Link>
          {token ? (
            <Link to="/profile" className="btn home-hero__cta home-hero__cta--ghost">
              Открыть профиль
            </Link>
          ) : (
            <Link to="/register" className="btn home-hero__cta home-hero__cta--ghost">
              Создать аккаунт
            </Link>
          )}
        </div>
      </section>

      <section className="home-section">
        <h2 className="home-section__title">Зачем это нужно</h2>
        <p className="home-section__text home-section__text--center">
          Когда едете не один, быстро теряются договоренности: кто за что платил, куда всем удобнее,
          что выбрать из вариантов. TripTogether помогает держать поездку в одном пространстве.
        </p>
      </section>

      <section className="home-section">
        <h2 className="home-section__title">Возможности</h2>
        <ul className="home-features">
          <li className="home-feature card">
            <span className="home-feature__icon" aria-hidden>🗓️</span>
            <h3 className="home-feature__name">Поездки</h3>
            <p className="home-feature__desc">Создавайте поездки, приглашайте участников и держите все в одном месте.</p>
          </li>
          <li className="home-feature card">
            <span className="home-feature__icon" aria-hidden>🗳️</span>
            <h3 className="home-feature__name">Голосования</h3>
            <p className="home-feature__desc">Быстро собирайте мнение группы и принимайте решения вместе.</p>
          </li>
          <li className="home-feature card">
            <span className="home-feature__icon" aria-hidden>💰</span>
            <h3 className="home-feature__name">Бюджет</h3>
            <p className="home-feature__desc">Фиксируйте расходы и смотрите, кто кому должен.</p>
          </li>
          <li className="home-feature card">
            <span className="home-feature__icon" aria-hidden>💬</span>
            <h3 className="home-feature__name">Чат</h3>
            <p className="home-feature__desc">Обсуждайте планы в общем чате каждой поездки.</p>
          </li>
        </ul>
      </section>

      <section className="home-section">
        <h2 className="home-section__title">Планирование без лишнего</h2>
        <p className="home-section__text home-section__text--center">
          Смотрите актуальную информацию в одном месте и быстро договаривайтесь с друзьями — от идей до итоговых решений.
        </p>
        <div className="home-previews">
          <article className="home-preview">
            <img
              className="home-preview__mock home-preview__mock--board"
              src="/home-previews/board.png"
              alt="Пример интерфейса: доска поездки"
            />
            <h3 className="home-preview__title">Доска поездки</h3>
            <p className="home-preview__text">Участники, голосования, расходы и чат в одном окне.</p>
          </article>
          <article className="home-preview">
            <img
              className="home-preview__mock home-preview__mock--map"
              src="/home-previews/map.png"
              alt="Пример интерфейса: карта поездки"
            />
            <h3 className="home-preview__title">Поездки + карта</h3>
            <p className="home-preview__text">Список поездок и отметки направлений на карте.</p>
          </article>
          <article className="home-preview">
            <img
              className="home-preview__mock home-preview__mock--profile"
              src="/home-previews/profile.png"
              alt="Пример интерфейса: профиль пользователя"
            />
            <h3 className="home-preview__title">Профиль</h3>
            <p className="home-preview__text">Имя, фамилия и фото профиля в удобной форме.</p>
          </article>
        </div>
      </section>

      <section className="home-section home-section--cta">
        <h2 className="home-section__title">Готовы начать?</h2>
        <p className="home-section__text">
          Создайте поездку, пригласите друзей и попробуйте совместное планирование в действии.
        </p>
        <div className="home-hero__actions">
          <Link to="/trips" className="btn home-hero__cta">Открыть поездки</Link>
          {!token && <Link to="/register" className="btn home-hero__cta home-hero__cta--ghost">Зарегистрироваться</Link>}
        </div>
      </section>
    </div>
  )
}
