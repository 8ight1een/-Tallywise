import { useRef, useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router'
import AuthFrame from '../components/AuthFrame'
import Icon from '../components/Icon'
import { errorText, json, request } from '../api'
import type { User } from '../types'
export default function AuthPage({ onLogin }: { onLogin: (user: User) => void }) {
  const register = useLocation().pathname === '/register'
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [message, setMessage] = useState('')
  const [pending, setPending] = useState(false)
  const lock = useRef(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (lock.current) return
    if (register && !nickname.trim()) {
      setMessage('昵称不能全是空格')
      return
    }
    lock.current = true
    setPending(true)
    setMessage('')
    try {
      if (register) {
        await request<User>(
          '/auth/register',
          json('POST', {
            email: email.trim(),
            password,
            nickname: nickname.trim(),
          }),
        )
        navigate('/login', { replace: true })
        setPassword('')
        setMessage('注册成功，请登录。')
      } else {
        const result = await request<{ user: User; message: string }>(
          '/auth/login',
          json('POST', { email: email.trim(), password }),
        )
        setPassword('')
        onLogin(result.user)
      }
    } catch (error) {
      setMessage(errorText(error))
    } finally {
      lock.current = false
      setPending(false)
    }
  }
  return (
    <AuthFrame>
      <div className="welcome-icon">
        <Icon name="book" />
      </div>
      <h1 id="login-title">{register ? '开启你的有数生活。' : '欢迎回来。'}</h1>
      <p className="subtitle">
        {register ? '创建账户，从第一笔记录开始。' : '登录你的账本，接着记录生活。'}
      </p>
      <form onSubmit={submit}>
        <fieldset disabled={pending} style={{ border: 0, padding: 0, margin: 0 }}>
          {register && (
            <div className="field">
              <label htmlFor="nickname">昵称</label>
              <div className="input-wrap">
                <Icon name="user" />
                <input
                  id="nickname"
                  required
                  maxLength={20}
                  autoComplete="nickname"
                  value={nickname}
                  onChange={(e) => setNickname(e.currentTarget.value)}
                />
              </div>
            </div>
          )}
          <div className="field">
            <label htmlFor="email">邮箱地址</label>
            <div className="input-wrap">
              <Icon name="mail" />
              <input
                id="email"
                type="email"
                required
                autoComplete="username"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.currentTarget.value)}
              />
            </div>
          </div>
          <div className="field">
            <label htmlFor="password">密码</label>
            <div className="input-wrap">
              <Icon name="lock" />
              <input
                id="password"
                type="password"
                required
                minLength={register ? 8 : 1}
                maxLength={32}
                autoComplete={register ? 'new-password' : 'current-password'}
                placeholder="请输入你的密码"
                value={password}
                onChange={(e) => setPassword(e.currentTarget.value)}
              />
            </div>
          </div>
          <p className="form-error" role="status">
            {message}
          </p>
          <button className="login-button" type="submit">
            {pending ? '请稍候…' : register ? '创建账户' : '登 录'}
            <Icon name="arrow" />
          </button>
        </fieldset>
      </form>
      <p className="register">
        {register ? '已有账户？' : '还没有账户？'}
        <button
          className="text-button"
          type="button"
          disabled={pending}
          onClick={() => {
            navigate(register ? '/login' : '/register')
            setPassword('')
            setMessage('')
          }}
        >
          {register ? '返回登录' : '创建一个新账户'}
        </button>
      </p>
      <p className="quiet-note">
        <Icon name="leaf" />
        每一天，都可以从一笔记录开始。
      </p>
    </AuthFrame>
  )
}