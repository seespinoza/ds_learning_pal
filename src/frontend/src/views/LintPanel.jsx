import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import api from '../api/client'

const SEVERITY_COLORS = {
  error: 'text-red-400 bg-red-900/20 border-red-800',
  warning: 'text-yellow-400 bg-yellow-900/20 border-yellow-800',
}

export default function LintPanel() {
  const [report, setReport] = useState(null)

  const lintMut = useMutation({
    mutationFn: () => api.post('/lint').then(r => r.data),
    onSuccess: setReport,
  })

  const nodeIssues = report?.per_node_findings?.flatMap(f =>
    f.issues.map(i => ({ ...i, node: f.node }))
  ) ?? []
  const crossIssues = report?.cross_node_issues ?? []
  const totalIssues = nodeIssues.length + crossIssues.length

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Lint</h1>
        <button
          onClick={() => lintMut.mutate()}
          disabled={lintMut.isPending}
          className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium"
        >
          {lintMut.isPending ? 'Scanning…' : 'Run Lint'}
        </button>
      </div>

      {lintMut.isError && (
        <p className="text-red-400 bg-red-900/20 border border-red-800 rounded-lg px-4 py-3 text-sm">
          {lintMut.error?.message}
        </p>
      )}

      {report && (
        <div className="space-y-5">
          <div className="bg-slate-800 rounded-xl p-4 flex gap-6">
            <Stat label="Nodes scanned" value={report.nodes_scanned ?? 0} />
            <Stat label="Issues found" value={totalIssues} highlight={totalIssues > 0} />
            <Stat label="Node issues" value={nodeIssues.length} />
            <Stat label="Cross-node" value={crossIssues.length} />
          </div>

          {totalIssues === 0 && (
            <p className="text-emerald-400 text-center py-8">Graph looks clean — no issues found.</p>
          )}

          {nodeIssues.length > 0 && (
            <Section title="Per-Node Issues">
              {nodeIssues.map((issue, i) => (
                <IssueRow key={i} issue={issue} showNode />
              ))}
            </Section>
          )}

          {crossIssues.length > 0 && (
            <Section title="Cross-Node Issues">
              {crossIssues.map((issue, i) => (
                <IssueRow key={i} issue={issue} />
              ))}
            </Section>
          )}
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, highlight }) {
  return (
    <div className="text-center">
      <div className={`text-2xl font-bold ${highlight ? 'text-yellow-400' : 'text-white'}`}>{value}</div>
      <div className="text-xs text-slate-400 mt-0.5">{label}</div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="bg-slate-800 rounded-xl p-5 space-y-2">
      <h2 className="text-base font-medium text-white mb-3">{title}</h2>
      {children}
    </div>
  )
}

function IssueRow({ issue, showNode }) {
  const sev = issue.severity ?? 'warning'
  const colorClass = SEVERITY_COLORS[sev] ?? SEVERITY_COLORS.warning
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${colorClass}`}>
      <div className="flex items-center gap-2 mb-0.5">
        <span className="uppercase text-xs font-mono font-bold">{sev}</span>
        <span className="text-xs font-mono opacity-70">{issue.type}</span>
        {showNode && issue.node && (
          <span className="text-xs opacity-80">· {issue.node}</span>
        )}
        {issue.nodes && (
          <span className="text-xs opacity-80">· {issue.nodes.join(', ')}</span>
        )}
      </div>
      <p className="opacity-90">{issue.detail}</p>
    </div>
  )
}
