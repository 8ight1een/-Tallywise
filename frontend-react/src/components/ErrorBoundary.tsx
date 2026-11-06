import { Component, type ReactNode } from 'react'
export default class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  componentDidCatch() {
    console.error(
      '界面渲染失败，请记录页面路径和构建版本；不要提交密码或账本内容。',
    )
  }
  render() {
    if (this.state.failed)
      return (
        <div className="status" role="alert">
          页面暂时无法显示。
          <button onClick={() => window.location.reload()}>重新加载</button>
        </div>
      )
    return this.props.children
  }
}