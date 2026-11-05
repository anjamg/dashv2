import { lazy, Suspense, useState } from 'react'
import { NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Activity, BarChart3, Clock3, CloudSun, FileUp, LogOut, Menu, Phone, Tags, Umbrella, X } from 'lucide-react'

const Login = lazy(() => import('./pages/login'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Calls = lazy(() => import('./pages/Calls'))
const Leaves = lazy(() => import('./pages/Leaves'))
const Tarifs = lazy(() => import('./pages/Tarifs'))
const TimeTracking = lazy(() => import('./pages/TimeTracking'))
const Imports = lazy(() => import('./pages/Imports'))
const Meteo = lazy(() => import('./pages/Meteo'))

const navItems = [
  { to: '/', label: 'Tableau de bord', icon: BarChart3 },
  { to: '/calls', label: 'Appels', icon: Phone },
  { to: '/time', label: 'Temps & ETP', icon: Clock3 },
  { to: '/meteo', label: 'Météo', icon: CloudSun },
  { to: '/leaves', label: 'Congés', icon: Umbrella },
  { to: '/tarifs', label: 'Tarifs & agences', icon: Tags },
  { to: '/imports', label: 'Imports', icon: FileUp },
]

function getUserInitial() {
  try {
    const user = JSON.parse(localStorage.getItem('vita_user') || '{}')
    return typeof user.username === 'string' && user.username.trim() ? user.username.trim()[0].toUpperCase() : 'V'
  } catch {
    return 'V'
  }
}

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const token = localStorage.getItem('vita_token')

  if (!token || location.pathname === '/login') return <Suspense fallback={<div className="app-loading">Chargement…</div>}><Login /></Suspense>

  function logout() {
    localStorage.removeItem('vita_token')
    localStorage.removeItem('vita_user')
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand">
          <span className="brand-mark"><Activity size={21} strokeWidth={2.5} /></span>
          <span><strong>VITA</strong><small>ESPACE DE PILOTAGE</small></span>
        </NavLink>
        <p className="nav-caption">ESPACE DE TRAVAIL</p>
        <nav className="side-nav">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
              <Icon size={18} strokeWidth={1.8} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="profile-chip"><span className="avatar">{getUserInitial()}</span><span className="profile-label">Espace sécurisé</span></div>
          <button className="logout-button" onClick={logout}><LogOut size={17} /><span>Déconnexion</span></button>
        </div>
      </aside>

      <div className="mobile-header">
        <NavLink to="/" className="brand">
          <span className="brand-mark"><Activity size={20} /></span><strong>VITA</strong>
        </NavLink>
        <button className="mobile-menu-button" onClick={() => setMenuOpen((open) => !open)} aria-label={menuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}>
          {menuOpen ? <X size={21} /> : <Menu size={21} />}
        </button>
        {menuOpen && <nav className="mobile-nav">{navItems.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} onClick={() => setMenuOpen(false)}><Icon size={17} />{label}</NavLink>)}</nav>}
      </div>

      <main className="main-content">
        <Suspense fallback={<div className="app-loading">Chargement de la page…</div>}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/calls" element={<Calls />} />
          <Route path="/leaves" element={<Leaves />} />
          <Route path="/tarifs" element={<Tarifs />} />
          <Route path="/time" element={<TimeTracking />} />
          <Route path="/imports" element={<Imports />} />
          <Route path="/meteo" element={<Meteo />} />
          <Route path="*" element={<Dashboard />} />
        </Routes>
        </Suspense>
      </main>
    </div>
  )
}
