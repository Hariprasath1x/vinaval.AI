import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ToastProvider } from './components/Toast'
import { ProtectedRoute } from './components/ProtectedRoute'
import LandingPage from './pages/LandingPage'
import SelectExam from './pages/SelectExam'
import Dashboard from './pages/Dashboard'
import SpacePage from './pages/SpacePage'

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            {/* Public */}
            <Route path="/" element={<LandingPage />} />

            {/* Protected */}
            <Route
              path="/select-exam"
              element={
                <ProtectedRoute>
                  <SelectExam />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            {/* Learning Space — new (create/redirect) */}
            <Route
              path="/space/new"
              element={
                <ProtectedRoute>
                  <SpacePage />
                </ProtectedRoute>
              }
            />
            {/* Learning Space — existing */}
            <Route
              path="/space/:id"
              element={
                <ProtectedRoute>
                  <SpacePage />
                </ProtectedRoute>
              }
            />

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  )
}
