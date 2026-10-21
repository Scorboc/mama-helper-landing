import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'
import './palette-lock.css'
import './glass-theme.css'
import './pages/parent-app.css'
import './ux-refinements.css'
import './room-experience.css'
import './room-olive.css'
import './shared-room-theme.css'
import './room-structure.css'

createRoot(document.getElementById("root")!).render(<App />);
