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
  isCustomerUser,
  isPendingAccessUser,
  isSubcontractorUser,
  resolvePostLoginPath,
  subscribeToAuthChanges,
  syncStoredProfileUser,
} from './auth'
import { getCurrentProfile } from './api'
import './index.css'

const SIDEBAR_COLLAPSED_STORAGE_KEY = 'rayadee_sidebar_collapsed'

function getStoredSidebarCollapsed() {
  if (typeof window === 'undefined') return false
  try {
    return window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

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
const DailyReportsPage = lazy(() => import('./DailyReportsPage'))
const ProjectReportsPage = lazy(() => import('./ProjectReportsPage'))
const PaymentConfirmationPage = lazy(() => import('./PaymentConfirmationPage'))

function ProtectedLayout({
  adminOnly = false,
  ownerOnly = false,
  pendingOnly = false,
  customerOnly = false,
  subcontractorOnly = false,
  shell = true,
}) {
  const location = useLocation()
  const [authUser, setAuthUser] = useState(() => getStoredAuthUser())
  const [sessionToken, setSessionToken] = useState(() => getStoredSessionToken())
  const [sidebarCollapsed, setSidebarCollapsed] = useState(getStoredSidebarCollapsed)
  const profileSyncTokenRef = useRef('')

  const toggleSidebarCollapsed = () => {
    setSidebarCollapsed((current) => {
      const next = !current
      try {
        window.localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, String(next))
      } catch {
        // The layout still works when browser storage is unavailable.
      }
      return next
    })
  }

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
    const isSubcontractorLineEntry = (
      location.pathname === '/daily-reports/me'
      || location.pathname.startsWith('/payment-confirmation')
    )
    const isLineEntry = customerOnly || isSubcontractorLineEntry
    const loginParams = new URLSearchParams()

    if (isLineEntry) {
      loginParams.set('portal', customerOnly ? 'customer' : 'subcontractor')
      loginParams.set('returnTo', location.pathname + location.search)
      loginParams.set('autoLine', '1')
    }

    const loginQuery = loginParams.toString()
    const loginPath = loginQuery ? `/login?${loginQuery}` : '/login'
    return <Navigate to={loginPath} replace state={{ from: location.pathname }} />
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

  if (customerOnly && !isCustomerUser(authUser)) {
    return <Navigate to={resolvePostLoginPath(authUser)} replace />
  }

  if (subcontractorOnly && !isSubcontractorUser(authUser)) {
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
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapsed={toggleSidebarCollapsed}
      />
      <main className={`main-content${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
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
        <Route path="/daily-reports" element={<DailyReportsPage />} />
      </Route>

      <Route element={<ProtectedLayout />}>
        <Route path="/input" element={<InputPage />} />
        <Route path="/inspection/tasks" element={<InspectionTasksPage />} />
        <Route path="/profile/me" element={<ProfilePage />} />
        <Route path="/daily-reports/me" element={<DailyReportsPage />} />
      </Route>

      <Route element={<ProtectedLayout customerOnly shell={false} />}>
        <Route path="/project-reports" element={<ProjectReportsPage />} />
      </Route>

      <Route element={<ProtectedLayout subcontractorOnly />}>
        <Route path="/payment-confirmation" element={<PaymentConfirmationPage />} />
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
