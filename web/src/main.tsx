import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import './styles/tokens.css'
import './index.css'
import './i18n'
import Home from './routes/w/Home'
import Job from './routes/w/Job'
import Stock from './routes/w/Stock'
import DashboardShell from './routes/d/DashboardShell'
import ImportDashboard from './routes/d/Import'
import Knowledge from './routes/d/Knowledge'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={new QueryClient()}>
      <BrowserRouter>
        <Routes>
          <Route path="/w" element={<Home />} />
          <Route path="/w/job/:id" element={<Job />} />
          <Route path="/w/stock" element={<Stock />} />
          <Route path="/d/knowledge" element={<DashboardShell><Knowledge /></DashboardShell>} />
          <Route path="/d/import" element={<DashboardShell><ImportDashboard /></DashboardShell>} />
          <Route path="*" element={<Navigate to="/w" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
