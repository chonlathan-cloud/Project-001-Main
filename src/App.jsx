import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './components/MainLayout'
import DashboardPage from './DashboardPage'
import ProjectPage from './ProjectPage'
import ProjectDetailPage from './ProjectDetailPage'
import InsightsPage from './InsightsPage'
import InputPage from './InputPage'
import ChatAIPage from './ChatAIPage'
import SettingPage from './SettingPage'
import ProfilePage from './ProfilePage'
import LoginPage from './LoginPage'
import SignUpPage from './SignUpPage'
import './index.css'

function App() {
  const isAuthenticated = localStorage.getItem('isAuthenticated') === 'true';

  return (
    <Router>
      <Routes>
        <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        
        <Route element={isAuthenticated ? <MainLayout /> : <Navigate to="/login" replace />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/project" element={<ProjectPage />} />
          <Route path="/project/detail" element={<ProjectDetailPage />} />
          <Route path="/insights" element={<InsightsPage />} />
          <Route path="/input" element={<InputPage />} />
          <Route path="/chat-ai" element={<ChatAIPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/setting" element={<SettingPage />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App
