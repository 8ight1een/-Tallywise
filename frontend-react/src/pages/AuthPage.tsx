import AuthFrame from '../components/AuthFrame'
import Icon from '../components/Icon'
export default function AuthPage() {
  return (
    <AuthFrame>
      <div className="welcome-icon">
        <Icon name="book" />
      </div>
      <h1 id="login-title">欢迎回来。</h1>
      <p className="subtitle">登录你的账本，接着记录生活。</p>
      <form onSubmit={(event) => event.preventDefault()}>
        <div className="field">
          <label htmlFor="email">邮箱地址</label>
          <div className="input-wrap">
            <Icon name="mail" />
            <input id="email" type="email" autoComplete="username" required />
          </div>
        </div>
        <div className="field">
          <label htmlFor="password">密码</label>
          <div className="input-wrap">
            <Icon name="lock" />
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </div>
        </div>
        <button className="login-button" disabled type="submit">
          登 录<Icon name="arrow" />
        </button>
      </form>
      <p className="register">
        还没有账户？
        <button disabled className="text-button" type="button">
          创建一个新账户
        </button>
      </p>
      <p className="quiet-note">
        <Icon name="leaf" />
        每一天，都可以从一笔记录开始。
      </p>
    </AuthFrame>
  )
}
