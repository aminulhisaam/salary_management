import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from './auth/ProtectedRoute'
import { AppShell } from './components/AppShell'
import { EmployeeDetailPage } from './pages/EmployeeDetailPage'
import { EmployeeListPage } from './pages/EmployeeListPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'

export function AppRoutes() {
  return (
    <AppShell>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<Navigate replace to="/employees" />} />
        <Route path="/employees" element={<ProtectedRoute><EmployeeListPage /></ProtectedRoute>} />
        <Route
          path="/insights"
          element={<ProtectedRoute><Suspense fallback={null}><InsightsPage /></Suspense></ProtectedRoute>}
        />
        <Route
          path="/employees/:employeeId"
          element={<ProtectedRoute><EmployeeDetailPage /></ProtectedRoute>}
        />
        <Route path="*" element={<Navigate replace to="/employees" />} />
      </Routes>
    </AppShell>
  )
}
const InsightsPage = lazy(() => import('./pages/InsightsPage').then((module) => ({ default: module.InsightsPage })))
