import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Fonts are bundled with the app (not loaded from Google), so opening the site
// contacts no third party. Bricolage's 'standard' file has the weight, width and
// optical-size axes; index.css uses the width axis (font-stretch).
import '@fontsource-variable/bricolage-grotesque/standard.css'
import '@fontsource/dm-mono/400.css'
import '@fontsource/dm-mono/500.css'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
