import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { FeedList } from './pages/FeedList'
import { FeedEntries } from './pages/FeedEntries'
import { FeedEdit } from './pages/FeedEdit'
import { RecentEntries } from './pages/RecentEntries'
import { ArticleReader } from './pages/ArticleReader'
import { ReaderView } from './pages/ReaderView'
import { Recommendations } from './pages/Recommendations'
import { Settings } from './pages/Settings'
import { HandlerConfig } from './pages/HandlerConfig'
import { Onboarding } from './pages/Onboarding'
import { About } from './pages/About'
import { Agent } from './pages/Agent'
import { ReaderProvider } from './context/ReaderContext'

function App() {
  return (
    <BrowserRouter basename="/_app">
      <ReaderProvider>
        <Routes>
          <Route path="/onboarding" element={<Onboarding />} />
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/feeds" element={<FeedList />} />
            <Route path="/feeds/:id" element={<FeedEntries />} />
            <Route path="/feeds/:id/edit" element={<FeedEdit />} />
            <Route path="/feeds/new" element={<FeedEdit />} />
            <Route path="/recent" element={<RecentEntries />} />
            <Route path="/read/:id" element={<ArticleReader />} />
            <Route path="/reader" element={<ReaderView />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/settings/handlers/:type" element={<HandlerConfig />} />
            <Route path="/agent" element={<Agent />} />
            <Route path="/about" element={<About />} />
          </Route>
        </Routes>
      </ReaderProvider>
    </BrowserRouter>
  )
}

export default App
