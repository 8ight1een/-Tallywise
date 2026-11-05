import type { ReactNode } from 'react'
import Icon from './Icon'
export default function AuthFrame({ children }: { children: ReactNode }) {
  return (
    <div className="auth-page">
      <div className="page">
        <header className="topbar">
          <div className="brand">
            <span className="brand-mark">
              <Icon name="logo" />
            </span>
            <span>
              tallywise<span className="brand-dot">.</span>
            </span>
          </div>
        </header>
        <main className="shell">
          <section className="story" aria-labelledby="story-title">
            <div className="eyebrow">A LITTLE CLARITY, EVERY DAY</div>
            <h2 id="story-title">
              把日子，
              <br />
              <span>记得清楚。</span>
            </h2>
            <p className="story-copy">
              一杯咖啡，一次出发，一点小小的积累。
              <br />
              让每一笔收支，都成为生活有迹可循的一部分。
            </p>
            <div className="story-footer">
              <Icon name="leaf" />
              <div>
                <b>从一笔记录，慢慢开始。</b>
                <span>不用复杂的计划，也能让生活更有数。</span>
              </div>
            </div>
          </section>
          <section className="login" aria-labelledby="login-title">
            <div className="login-inner">{children}</div>
          </section>
        </main>
        <footer className="page-footer">
          <span>© 2026 Tallywise</span>
          <span>简单记账 · 有数生活</span>
        </footer>
      </div>
    </div>
  )
}
