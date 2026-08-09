import { Component, type ErrorInfo, type ReactNode } from 'react'

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: string | null }
> {
  state = { error: null as string | null }

  static getDerivedStateFromError(error: unknown): { error: string } {
    return {
      error: error instanceof Error ? error.message : String(error)
    }
  }

  componentDidCatch(error: unknown, info: ErrorInfo): void {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="flex h-full min-h-screen items-center justify-center bg-[#e8f8f3] p-6 text-[#3e4a32]">
          <div className="max-w-xl rounded-lg border border-[#b5c4a1] bg-[#e8f8f3] p-5 shadow-lg">
            <h1 className="mb-2 text-lg font-semibold">页面运行出错</h1>
            <p className="break-words text-sm text-[#7a5a50]">{this.state.error}</p>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
