import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { formatUserDisplayName } from '../api/auth'

export function Layout() {
  const { user, token, logout } = useAuth()
  const location = useLocation()
  const displayName = formatUserDisplayName(user)
  const isTripPage = location.pathname.startsWith('/trip/')
  const isTripsPage = location.pathname === '/trips'
  const isHomePage = location.pathname === '/'
  const isProfilePage = location.pathname === '/profile'
  const isWideLayout = isTripPage || isTripsPage || isHomePage || isProfilePage

  return (
    <>
      <nav className="nav">
        <div className="nav-inner nav-inner--wide">
          <div className="nav-brand">
            <Link to="/" className="nav-logo">TripTogether</Link>
            <Link to="/trips" className="nav-link">Поездки</Link>
            <Link to="/profile" className="nav-link">Профиль</Link>
          </div>
          {token ? (
            <div className="nav-user">
              <span className="nav-username" title={displayName}>{displayName}</span>
              <button type="button" className="btn-nav" onClick={logout}>
                Выйти
              </button>
            </div>
          ) : (
            <div className="nav-auth">
              <Link to="/login" className="btn-nav nav-auth-link">Вход</Link>
              <Link to="/register" className="btn-nav nav-auth-link nav-auth-link--primary">Регистрация</Link>
            </div>
          )}
        </div>
      </nav>
      <main className={isWideLayout ? 'main-content main-content--wide' : 'container main-content'}>
        <Outlet />
      </main>
    </>
  )
}
