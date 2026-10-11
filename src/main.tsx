import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'
import './palette-lock.css'
import './glass-theme.css'
import './pages/parent-app.css'
import './ux-refinements.css'

createRoot(document.getElementById("root")!).render(<App />);
