import { type ReactNode, type CSSProperties } from 'react'

// ─── Button ──────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'warm' | 'danger' | 'ghost'

interface ButtonProps {
  children: ReactNode
  variant?: ButtonVariant
  onClick?: () => void
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
  style?: CSSProperties
  className?: string
}

export function Button({
  children,
  variant = 'primary',
  onClick,
  disabled,
  type = 'button',
  style,
  className = '',
}: ButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`retro-button retro-button-${variant} ${className}`}
      style={style}
    >
      {children}
    </button>
  )
}

// ─── Panel ───────────────────────────────────────────────────

interface PanelProps {
  children: ReactNode
  style?: CSSProperties
  className?: string
  compact?: boolean
}

export function Panel({ children, style, className = '', compact }: PanelProps) {
  return (
    <div
      className={`retro-panel ${className}`}
      style={{
        padding: compact ? '1rem' : '1.5rem',
        boxShadow: compact ? 'var(--shadow-panel-sm)' : 'var(--shadow-panel)',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

// ─── Input ───────────────────────────────────────────────────

interface InputProps {
  label?: string
  required?: boolean
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
  type?: string
  hint?: string
}

export function Input({
  label,
  required,
  value,
  onChange,
  placeholder,
  type = 'text',
  hint,
}: InputProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {label && (
        <label
          style={{
            fontFamily: 'var(--ff-display)',
            fontSize: 'var(--fs-xs)',
            textTransform: 'uppercase',
            letterSpacing: 'var(--tr-wider)',
          }}
        >
          {label}
          {required && <span style={{ color: 'var(--retro-rose)' }}> *</span>}
        </label>
      )}
      <input
        type={type}
        value={value ?? ''}
        onChange={(e) => onChange?.(e.target.value)}
        placeholder={placeholder}
        className="retro-input"
      />
      {hint && (
        <div
          style={{
            fontSize: 'var(--fs-sm)',
            color: 'var(--fg-3)',
            fontFamily: 'var(--ff-body)',
          }}
        >
          {hint}
        </div>
      )}
    </div>
  )
}

// ─── StatusBadge ─────────────────────────────────────────────

type SimStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed'
type CharStatus = 'Available' | 'In simulation'

const STATUS_STYLES: Record<string, { bg: string; color: string }> = {
  pending:        { bg: 'var(--bg-info-soft)',    color: 'var(--fg-1)' },
  running:        { bg: 'var(--bg-success-soft)', color: '#2a5a1a' },
  paused:         { bg: 'var(--bg-warn-soft)',    color: '#a14d1f' },
  completed:      { bg: 'var(--bg-info-soft)',    color: '#2a4a6a' },
  failed:         { bg: 'var(--bg-danger-soft)',  color: 'var(--retro-rose)' },
  Available:      { bg: 'var(--bg-info-soft)',    color: 'var(--fg-1)' },
  'In simulation':{ bg: 'var(--bg-success-soft)', color: '#2a5a1a' },
}

interface StatusBadgeProps {
  status: SimStatus | CharStatus | string
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const s = STATUS_STYLES[status] ?? STATUS_STYLES.pending
  return (
    <span
      className="retro-badge"
      style={{ background: s.bg, color: s.color, padding: '2px 10px' }}
    >
      {status}
    </span>
  )
}

// ─── EmptyState ──────────────────────────────────────────────

interface EmptyStateProps {
  children: ReactNode
}

export function EmptyState({ children }: EmptyStateProps) {
  return <div className="retro-empty-state">{children}</div>
}

// ─── DesignLink ──────────────────────────────────────────────
// Named DesignLink to avoid collision with react-router's Link.

interface DesignLinkProps {
  children: ReactNode
  onClick?: () => void
}

export function DesignLink({ children, onClick }: DesignLinkProps) {
  return (
    <a
      onClick={onClick}
      style={{
        color: 'var(--fg-link)',
        textDecoration: 'underline',
        textUnderlineOffset: '2px',
        fontWeight: 800,
        fontSize: 'var(--fs-sm)',
        cursor: 'pointer',
        fontFamily: 'var(--ff-display)',
        textTransform: 'uppercase',
        letterSpacing: 'var(--tr-normal)',
      }}
    >
      {children}
    </a>
  )
}
