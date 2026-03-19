import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { registerSW } from 'virtual:pwa-register'
import { setUpdateSW, notifyNeedRefresh } from './utils/pwaUpdate'
import './index.css'
import App from './App.tsx'

const updateSW = registerSW({
  immediate: true,
  onNeedRefresh() {
    setUpdateSW(updateSW)
    notifyNeedRefresh()
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
