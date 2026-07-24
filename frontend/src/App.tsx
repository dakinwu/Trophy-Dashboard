import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { ComingNextPage } from './pages/ComingNextPage'
import { LandingPage } from './pages/LandingPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OverviewPage } from './pages/OverviewPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="u/:username" element={<OverviewPage />} />
          <Route path="u/:username/games" element={<ComingNextPage title="Games" />} />
          <Route path="u/:username/timeline" element={<ComingNextPage title="Timeline" />} />
          <Route
            path="u/:username/milestones"
            element={<ComingNextPage title="Milestones" />}
          />
          <Route path="u/:username/data" element={<ComingNextPage title="Data" />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
