import React, { Suspense, lazy, useEffect, useState } from 'react'
import { BrowserRouter as Router, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Loading from './components/Loading'
import {
  getStoredAuthUser,
  getStoredSessionToken,
  isAdminUser,
  resolvePostLoginPath,
  subscribeToAuthChanges,
} from './auth'
import './index.css'

const DashboardPage = lazy(() => import('./DashboardPage'))
const ProjectPage = lazy(() => import('./ProjectPage'))
const ProjectDetailPage = lazy(() => import('./ProjectDetailPage'))
const InsightsPage = lazy(() => import('./InsightsPage'))
const InputPage = lazy(() => import('./InputPage'))
const ApprovalPage = lazy(() => import('./ApprovalPage'))
const ChatAIPage = lazy(() => import('./ChatAIPage'))
const SettingPage = lazy(() => import('./SettingPage'))
const ProfilePage = lazy(() => import('./ProfilePage'))
const LoginPage = lazy(() => import('./LoginPage'))
const SignUpPage = lazy(() => import('./SignUpPage'))
const LineCallbackPage = lazy(() => import('./LineCallbackPage'))

function ProtectedLayout({ adminOnly = false }) {
  const location = useLocation()
  const [authUser, setAuthUser] = useState(() => getStoredAuthUser())
  const [sessionToken, setSessionToken] = useState(() => getStoredSessionToken())

  useEffect(() => (
    subscribeToAuthChanges(() => {
      setAuthUser(getStoredAuthUser())
      setSessionToken(getStoredSessionToken())
    })
  ), [])

  if (!sessionToken) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (adminOnly && !isAdminUser(authUser)) {
    return <Navigate to={resolvePostLoginPath(authUser)} replace />
  }

  return (
    <>
      <Sidebar />
      <main className="main-content">
        <Suspense fallback={<Loading />}>
          <Outlet />
        </Suspense>
      </main>
    </>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={(
          <Suspense fallback={<Loading />}>
            <LoginPage />
          </Suspense>
        )}
      />
      <Route
        path="/signup"
        element={(
          <Suspense fallback={<Loading />}>
            <SignUpPage />
          </Suspense>
        )}
      />
      <Route
        path="/auth/line/callback"
        element={(
          <Suspense fallback={<Loading />}>
            <LineCallbackPage />
          </Suspense>
        )}
      />

      <Route element={<ProtectedLayout adminOnly />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/project" element={<ProjectPage />} />
        <Route path="/project/detail" element={<ProjectDetailPage />} />
        <Route path="/project/detail/:projectId" element={<ProjectDetailPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/approval" element={<ApprovalPage />} />
        <Route path="/chat-ai" element={<ChatAIPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/setting" element={<SettingPage />} />
      </Route>

      <Route element={<ProtectedLayout />}>
        <Route path="/input" element={<InputPage />} />
        <Route path="/profile/me" element={<ProfilePage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <Router>
      <AppRoutes />
    </Router>
  )
}

export default App
