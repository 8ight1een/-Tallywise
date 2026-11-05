import type { ReactNode } from 'react'
import Icon from './Icon'
import { NavLink } from 'react-router'
import { labels, type Page } from '../workspace'
type Props = {
  page: Page
  name: string
  onLogout: () => void
  logoutBusy?: boolean
  children: ReactNode
}
export default function Workspace({
  page,
  name,
  onLogout,
  logoutBusy = false,
  children,
}: Props) {
  return (
    <div className="workspace">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand">
          <span className="brand-mark">
            <Icon name="logo" />
          </span>
          <span>
            tallywise<span style={{ color: '#8fa46d' }}>.</span>
          </span>
        </div>
        <div className="brand-sub">有数的生活</div>
        <div className="nav-label">MY WORKSPACE</div>
        <nav className="nav">
          {(Object.keys(labels) as Page[]).map((item, index) => (
            <NavLink
              key={item}
              to={'/' + item}
              end
              className={({ isActive }) => (isActive ? 'active' : '')}
            >
              <Icon name={['grid', 'list', 'wallet', 'tag'][index]} />
              <span>{labels[item]}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="side-note">
            <Icon name="leaf" />
            <strong>每一笔，都有迹可循。</strong>
            <p>
              记录生活里的小事，
              <br />
              慢慢找到自己的节奏。
            </p>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            我的工作台 <span>/</span>
            <b>{labels[page]}</b>
          </div>
          <div className="mobile-brand">
            <Icon name="logo" />
            tallywise.
          </div>
          <div className="user-menu">
            <div className="user-identity">
              <span className="avatar">
                <Icon name="user" />
              </span>
              <span className="user-name" title={name}>
                {name}
              </span>
            </div>
            <button
              type="button"
              className="logout-button"
              disabled={logoutBusy}
              onClick={onLogout}
            >
              <Icon name="logout" />
              退出登录
            </button>
          </div>
        </header>
        {children}
        <footer className="footer">
          <span>TALLYWISE · 让生活，心中有数。</span>
        </footer>
      </main>
    </div>
  )
}
