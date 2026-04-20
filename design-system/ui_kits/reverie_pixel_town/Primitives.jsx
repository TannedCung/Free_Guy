const { useState } = React;

// ─── Primitives ─────────────────────────────────────────────

function Button({ children, variant = 'primary', onClick, disabled, type = 'button', style, className = '' }) {
  const variants = {
    primary: { background: 'var(--retro-sky)', color: 'var(--retro-ink)' },
    warm:    { background: 'var(--retro-sun)', color: 'var(--retro-ink)' },
    danger:  { background: 'var(--retro-rose)', color: '#fff' },
    ghost:   { background: '#fff', color: 'var(--retro-ink)' },
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rpt-btn ${className}`}
      style={{ ...variants[variant], ...style }}
    >{children}</button>
  );
}

function NavLink({ children, active, onClick, relative, badge }) {
  return (
    <a
      onClick={onClick}
      className="rpt-navlink"
      style={{
        background: active ? 'var(--retro-orange)' : 'var(--retro-sun)',
        position: relative ? 'relative' : undefined,
      }}
    >{children}
      {badge != null && badge > 0 && (
        <span className="rpt-badge" style={{
          position: 'absolute', top: '-10px', right: '-12px',
          background: 'var(--retro-rose)', color: '#fff',
          minWidth: '1rem', minHeight: '1rem', padding: '0 4px',
          fontSize: '.58rem',
        }}>{badge}</span>
      )}
    </a>
  );
}

function Panel({ children, style, className = '', compact }) {
  return (
    <div
      className={`rpt-panel ${className}`}
      style={{
        padding: compact ? '1rem' : '1.5rem',
        boxShadow: compact ? '4px 4px 0 var(--retro-shadow)' : '6px 6px 0 var(--retro-shadow)',
        ...style,
      }}
    >{children}</div>
  );
}

function Input({ label, required, value, onChange, placeholder, type = 'text', hint }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {label && (
        <label style={{
          fontFamily: 'var(--ff-display)', fontSize: '.64rem',
          textTransform: 'uppercase', letterSpacing: '.06em',
        }}>
          {label}{required && <span style={{ color: 'var(--retro-rose)' }}> *</span>}
        </label>
      )}
      <input
        type={type}
        value={value || ''}
        onChange={e => onChange?.(e.target.value)}
        placeholder={placeholder}
        className="rpt-input"
      />
      {hint && <div style={{ fontSize: '.7rem', color: 'var(--fg-3)', fontFamily: 'var(--ff-body)' }}>{hint}</div>}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    pending:   { bg: 'var(--bg-info-soft)',   color: 'var(--fg-1)' },
    running:   { bg: '#d4f0c8',               color: '#2a5a1a' },
    paused:    { bg: 'var(--bg-warn-soft)',   color: '#a14d1f' },
    completed: { bg: 'var(--bg-info-soft)',   color: '#2a4a6a' },
    failed:    { bg: 'var(--bg-danger-soft)', color: 'var(--retro-rose)' },
    Available: { bg: 'var(--bg-info-soft)',   color: 'var(--fg-1)' },
    'In simulation': { bg: '#d4f0c8', color: '#2a5a1a' },
  };
  const s = map[status] || map.pending;
  return (
    <span className="rpt-badge" style={{ background: s.bg, color: s.color, padding: '2px 10px' }}>
      {status}
    </span>
  );
}

function EmptyState({ children }) {
  return (
    <div style={{
      border: '2px dashed var(--retro-sky)',
      background: '#fff', padding: '1.2rem', textAlign: 'center',
      color: 'var(--fg-3)', fontSize: '.85rem', fontFamily: 'var(--ff-body)',
    }}>{children}</div>
  );
}

function Link({ children, onClick }) {
  return (
    <a onClick={onClick} style={{
      color: 'var(--retro-rose)', textDecoration: 'underline',
      textUnderlineOffset: '2px', fontWeight: 800, fontSize: '.72rem',
      cursor: 'pointer', fontFamily: 'var(--ff-display)',
      textTransform: 'uppercase', letterSpacing: '.04em',
    }}>{children}</a>
  );
}

Object.assign(window, { Button, NavLink, Panel, Input, StatusBadge, EmptyState, Link });
