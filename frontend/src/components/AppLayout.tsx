import { Outlet } from 'react-router-dom'
import { TopNav } from './TopNav'

/** Shared shell rendered on every route: top nav bar + routed page content. */
export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-bg text-text">
      <TopNav />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}
