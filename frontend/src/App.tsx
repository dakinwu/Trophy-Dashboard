import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { DataPage } from './pages/DataPage'
import { GamesPage } from './pages/GamesPage'
import { LandingPage } from './pages/LandingPage'
import { MilestonesPage } from './pages/MilestonesPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OverviewPage } from './pages/OverviewPage'
import { TimelinePage } from './pages/TimelinePage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="u/:username" element={<OverviewPage />} />
          <Route path="u/:username/games" element={<GamesPage />} />
          <Route path="u/:username/timeline" element={<TimelinePage />} />
          <Route path="u/:username/milestones" element={<MilestonesPage />} />
          <Route path="u/:username/data" element={<DataPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
