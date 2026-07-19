import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import LineEntryBootstrap from './components/LineEntryBootstrap.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <LineEntryBootstrap>
      <App />
    </LineEntryBootstrap>
  </StrictMode>,
)
