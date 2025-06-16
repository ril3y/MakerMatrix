import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { useEffect } from 'react'
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext'

// Layouts
import MainLayout from '@/components/layouts/MainLayout'
import AuthLayout from '@/components/layouts/AuthLayout'

// Pages
import LoginPage from '@/pages/auth/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import PartsPage from '@/pages/parts/PartsPage'
import PartDetailsPage from '@/pages/parts/PartDetailsPage'
import EditPartPage from '@/pages/parts/EditPartPage'
import LocationsPage from '@/pages/locations/LocationsPage'
import CategoriesPage from '@/pages/categories/CategoriesPage'
import UsersPage from '@/pages/users/UsersPage'
import SettingsPage from '@/pages/settings/SettingsPage'
import AnalyticsDashboard from '@/pages/analytics/AnalyticsDashboard'
import UnauthorizedPage from '@/pages/UnauthorizedPage'
import NotFoundPage from '@/pages/NotFoundPage'

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
              
              {/* User Management - Admin Only */}
              <Route path="/users" element={
                <ProtectedRoute requireRole="admin">
                  <UsersPage />
                </ProtectedRoute>
              } />
              
              {/* Settings */}
              <Route path="/settings" element={<SettingsPage />} />
              
              {/* Analytics */}
              <Route path="/analytics" element={<AnalyticsDashboard />} />
            </Route>
          </Route>

          {/* Public Routes */}
          <Route path="/unauthorized" element={<UnauthorizedPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
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
      <AppContent />
    </ThemeProvider>
  )
}

export default App