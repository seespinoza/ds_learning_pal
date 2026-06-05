import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LoginPage from './views/LoginPage'
import GraphExplorer from './views/GraphExplorer'
import IngestPanel from './views/IngestPanel'
import LintPanel from './views/LintPanel'

const qc = new QueryClient()

const NAV = [
  { id: 'graph', label: 'Graph' },
  { id: 'ingest', label: 'Ingest' },
  { id: 'lint', label: 'Lint' },
]

function Shell() {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [view, setView] = useState('graph')

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
  }

  if (!token) {
    return <LoginPage onLogin={setToken} />
  }

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between px-5 py-3 bg-slate-900 border-b border-slate-700 shrink-0">
        <span className="font-semibold text-white text-sm tracking-tight">DS Learning Pal</span>
        <nav className="flex gap-1">
          {NAV.map(n => (
            <button
              key={n.id}
              onClick={() => setView(n.id)}
              className={`px-3 py-1.5 rounded text-sm ${view === n.id ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
            >
              {n.label}
            </button>
          ))}
        </nav>
        <button onClick={logout} className="text-xs text-slate-500 hover:text-slate-300">Sign out</button>
      </header>

      <main className="flex-1 overflow-hidden flex flex-col">
        {view === 'graph' && <GraphExplorer />}
        {view === 'ingest' && <div className="flex-1 overflow-y-auto"><IngestPanel /></div>}
        {view === 'lint' && <div className="flex-1 overflow-y-auto"><LintPanel /></div>}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <Shell />
    </QueryClientProvider>
  )
}
