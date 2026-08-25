import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { LandingPage } from './pages/LandingPage'
import { NotFoundPage } from './pages/NotFoundPage'

const DataPage = lazy(() => import('./pages/DataPage').then((module) => ({ default: module.DataPage })))
const AdvisorPage = lazy(() =>
  import('./pages/AdvisorPage').then((module) => ({ default: module.AdvisorPage })),
)
const GameDetailPage = lazy(() =>
  import('./pages/GameDetailPage').then((module) => ({ default: module.GameDetailPage })),
)
const GamesPage = lazy(() => import('./pages/GamesPage').then((module) => ({ default: module.GamesPage })))
const MilestonesPage = lazy(() =>
  import('./pages/MilestonesPage').then((module) => ({ default: module.MilestonesPage })),
)
const OverviewPage = lazy(() =>
  import('./pages/OverviewPage').then((module) => ({ default: module.OverviewPage })),
)
const TimelinePage = lazy(() =>
  import('./pages/TimelinePage').then((module) => ({ default: module.TimelinePage })),
)

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<p className="p-6 text-sm text-muted">正在載入頁面…</p>}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<LandingPage />} />
            <Route path="u/:username" element={<OverviewPage />} />
            <Route path="u/:username/games" element={<GamesPage />} />
            <Route path="u/:username/advisor" element={<AdvisorPage />} />
            <Route path="u/:username/games/detail" element={<GameDetailPage />} />
            <Route path="u/:username/timeline" element={<TimelinePage />} />
            <Route path="u/:username/milestones" element={<MilestonesPage />} />
            <Route path="u/:username/data" element={<DataPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

export default App
