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
import './qa-accessibility.css'
import './input-viewport.css'
import { installInputViewport } from './lib/input-viewport'

const stopInputViewport = installInputViewport();
if (import.meta.hot) import.meta.hot.dispose(stopInputViewport);

createRoot(document.getElementById("root")!).render(<App />);
