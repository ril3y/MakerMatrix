import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { useEffect, lazy, Suspense } from 'react'
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext'
import { WebSocketProvider } from '@/contexts/WebSocketContext'

// Layouts (kept eager — shells around lazy pages)
import MainLayout from '@/components/layouts/MainLayout'
import AuthLayout from '@/components/layouts/AuthLayout'

// Pages (lazy — each becomes its own chunk so the initial bundle stays small)
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'))
const DashboardPage = lazy(() => import('@/pages/DashboardPage'))
const PartsPage = lazy(() => import('@/pages/parts/PartsPage'))
const PartDetailsPage = lazy(() => import('@/pages/parts/PartDetailsPage'))
const EditPartPage = lazy(() => import('@/pages/parts/EditPartPage'))
const LocationsPage = lazy(() => import('@/pages/locations/LocationsPage'))
const CategoriesPage = lazy(() => import('@/pages/categories/CategoriesPage'))
const ProjectsPage = lazy(() => import('@/pages/projects/ProjectsPage'))
const ToolsPage = lazy(() => import('@/pages/tools/ToolsPage'))
const UsersPage = lazy(() => import('@/pages/users/UsersPage'))
const SettingsPage = lazy(() => import('@/pages/settings/SettingsPage'))
const TasksPage = lazy(() => import('@/pages/tasks/TasksPage'))
const UnauthorizedPage = lazy(() => import('@/pages/UnauthorizedPage'))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'))

// Components
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import LoadingScreen from '@/components/ui/LoadingScreen'

function AppContent() {
  const { checkAuth, isLoading, isAuthenticated } = useAuthStore()
  const { isDarkMode } = useTheme()

  useEffect(() => {
    // Only check auth if we don't already have an authenticated state
    if (!isAuthenticated) {
      checkAuth()
    }
  }, [checkAuth, isAuthenticated])

  if (isLoading) {
    return <LoadingScreen />
  }

  return (
    <>
      <Router>
        <Suspense fallback={<LoadingScreen />}>
          <Routes>
            {/* Auth Routes */}
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<LoginPage />} />
            </Route>

            {/* Protected Routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<MainLayout />}>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />

                {/* Parts Management */}
                <Route path="/parts" element={<PartsPage />} />
                <Route path="/parts/:id" element={<PartDetailsPage />} />
                <Route path="/parts/:id/edit" element={<EditPartPage />} />

                {/* Location Management */}
                <Route path="/locations" element={<LocationsPage />} />

                {/* Category Management */}
                <Route path="/categories" element={<CategoriesPage />} />

                {/* Project Management */}
                <Route path="/projects" element={<ProjectsPage />} />

                {/* Tools Management */}
                <Route path="/tools" element={<ToolsPage />} />

                {/* Template Management - Redirect to Settings */}
                <Route
                  path="/templates"
                  element={<Navigate to="/settings?tab=templates" replace />}
                />

                {/* User Management - Admin Only */}
                <Route
                  path="/users"
                  element={
                    <ProtectedRoute requireRole="admin">
                      <UsersPage />
                    </ProtectedRoute>
                  }
                />

                {/* Settings */}
                <Route path="/settings" element={<SettingsPage />} />

                {/* Tasks Management */}
                <Route path="/tasks" element={<TasksPage />} />
              </Route>
            </Route>

            {/* Public Routes */}
            <Route path="/unauthorized" element={<UnauthorizedPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </Router>

      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: isDarkMode ? '#1f2937' : '#ffffff',
            color: isDarkMode ? '#e5e7eb' : '#111827',
            border: isDarkMode ? '1px solid #374151' : '1px solid #d1d5db',
          },
          success: {
            iconTheme: {
              primary: '#00ff9d',
              secondary: isDarkMode ? '#000000' : '#ffffff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#ffffff',
            },
          },
        }}
      />
    </>
  )
}

function App() {
  return (
    <ThemeProvider>
      <WebSocketProvider enableToastsByDefault={true} showConnectionStatus={true}>
        <AppContent />
      </WebSocketProvider>
    </ThemeProvider>
  )
}

export default App
