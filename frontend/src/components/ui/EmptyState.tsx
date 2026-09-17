import type { ReactNode } from 'react'
import './EmptyState.css'

interface EmptyStateProps {
  title: string
  message?: string
  action?: ReactNode
  tone?: 'default' | 'error'
}

export default function EmptyState({ title, message, action, tone = 'default' }: EmptyStateProps) {
  return (
    <div className={`empty-state${tone === 'error' ? ' empty-state--error' : ''}`} role="status">
      <div className="empty-state-icon" aria-hidden="true">
        {tone === 'error' ? '⚠️' : '🧺'}
      </div>
      <p className="empty-state-title">{title}</p>
      {message && <p className="empty-state-message">{message}</p>}
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  )
}
