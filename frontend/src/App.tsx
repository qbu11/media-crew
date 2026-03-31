import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './lib/queryClient'
import { AppLayout } from './components/layout/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { AgentsPage } from './pages/AgentsPage'
import { CrewsPage } from './pages/CrewsPage'
import { TasksPage } from './pages/TasksPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { SearchPage } from './pages/SearchPage'
import { ImagesPage } from './pages/ImagesPage'
import { ClientsPage } from './pages/ClientsPage'
import { ClientDetailPage } from './pages/ClientDetailPage'
import { ContentPage } from './pages/ContentPage'
import { ContentCreatePage } from './pages/ContentCreatePage'
import { ContentDraftsPage } from './pages/ContentDraftsPage'
import { ContentReviewPage } from './pages/ContentReviewPage'
import { PublishPage } from './pages/PublishPage'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            {/* 系统监控 */}
            <Route index element={<DashboardPage />} />
            <Route path="agents" element={<AgentsPage />} />
            <Route path="crews" element={<CrewsPage />} />
            <Route path="tasks" element={<TasksPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            {/* 内容运营 */}
            <Route path="content" element={<ContentPage />} />
            <Route path="content/create" element={<ContentCreatePage />} />
            <Route path="content/drafts" element={<ContentDraftsPage />} />
            <Route path="content/:id/review" element={<ContentReviewPage />} />
            <Route path="publish" element={<PublishPage />} />
            {/* 运营工具 */}
            <Route path="search" element={<SearchPage />} />
            <Route path="images" element={<ImagesPage />} />
            <Route path="clients" element={<ClientsPage />} />
            <Route path="clients/:id" element={<ClientDetailPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
