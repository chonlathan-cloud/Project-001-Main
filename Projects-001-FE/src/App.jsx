import React, { Suspense, lazy, useEffect, useRef, useState } from 'react'
import { BrowserRouter as Router, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Loading from './components/Loading'
import WorkspaceTopbar from './components/WorkspaceTopbar'
import {
  getStoredAuthUser,
  getStoredSessionToken,
  canAccessOwnerArea,
  isAdminPortalUser,
  isPendingAccessUser,
  resolvePostLoginPath,
  subscribeToAuthChanges,
  syncStoredProfileUser,
} from './auth'
import { getCurrentProfile } from './api'
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
const SupportPage = lazy(() => import('./SupportPage'))
const InspectionTasksPage = lazy(() => import('./InspectionTasksPage'))
const LoginPage = lazy(() => import('./LoginPage'))
const SignUpPage = lazy(() => import('./SignUpPage'))
const LineCallbackPage = lazy(() => import('./LineCallbackPage'))
const PendingApprovalPage = lazy(() => import('./PendingApprovalPage'))

function ProtectedLayout({ adminOnly = false, ownerOnly = false, pendingOnly = false, shell = true }) {
  const location = useLocation()
  const [authUser, setAuthUser] = useState(() => getStoredAuthUser())
  const [sessionToken, setSessionToken] = useState(() => getStoredSessionToken())
  const profileSyncTokenRef = useRef('')

  useEffect(() => (
    subscribeToAuthChanges(() => {
      setAuthUser(getStoredAuthUser())
      setSessionToken(getStoredSessionToken())
    })
  ), [])

  useEffect(() => {
    if (!sessionToken || pendingOnly || profileSyncTokenRef.current === sessionToken) return

    let isActive = true
    profileSyncTokenRef.current = sessionToken

    getCurrentProfile()
      .then((profile) => {
        if (!isActive || !profile?.user) return
        const syncedUser = syncStoredProfileUser(profile.user)
        if (syncedUser) {
          setAuthUser(syncedUser)
        }
      })
      .catch(() => {
        if (isActive && profileSyncTokenRef.current === sessionToken) {
          profileSyncTokenRef.current = ''
        }
      })

    return () => {
      isActive = false
    }
  }, [pendingOnly, sessionToken])

  if (!sessionToken) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (pendingOnly && !isPendingAccessUser(authUser)) {
    return <Navigate to={resolvePostLoginPath(authUser)} replace />
  }

  if (!pendingOnly && isPendingAccessUser(authUser)) {
    return <Navigate to="/pending-approval" replace />
  }

  if (adminOnly && !isAdminPortalUser(authUser)) {
    return <Navigate to={resolvePostLoginPath(authUser)} replace />
  }

  if (ownerOnly && !canAccessOwnerArea(authUser)) {
    return <Navigate to={resolvePostLoginPath(authUser)} replace />
  }

  if (!shell) {
    return (
      <Suspense fallback={<Loading />}>
        <Outlet />
      </Suspense>
    )
  }

  return (
    <>
      <Sidebar />
      <main className="main-content">
        <WorkspaceTopbar authUser={authUser} pathname={location.pathname} />
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

      <Route element={<ProtectedLayout pendingOnly shell={false} />}>
        <Route path="/pending-approval" element={<PendingApprovalPage />} />
      </Route>

      <Route element={<ProtectedLayout adminOnly ownerOnly />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/chat-ai" element={<ChatAIPage />} />
      </Route>

      <Route element={<ProtectedLayout adminOnly />}>
        <Route path="/project" element={<ProjectPage />} />
        <Route path="/project/detail" element={<ProjectDetailPage />} />
        <Route path="/project/detail/:projectId" element={<ProjectDetailPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/approval" element={<ApprovalPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/setting" element={<SettingPage />} />
        <Route path="/support" element={<SupportPage />} />
      </Route>

      <Route element={<ProtectedLayout />}>
        <Route path="/input" element={<InputPage />} />
        <Route path="/inspection/tasks" element={<InspectionTasksPage />} />
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
