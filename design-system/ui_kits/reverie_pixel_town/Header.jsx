const { useState } = React;

function Header({ user, pendingInvites, route, goto, onLogout }) {
  return (
    <header style={{
      background: 'var(--retro-sky)',
      borderBottom: '4px solid var(--retro-orange)',
      boxShadow: '0 6px 0 var(--retro-shadow)',
    }}>
      <div style={{
        maxWidth: '76rem', margin: '0 auto', padding: '14px 16px',
        display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap',
      }}>
        <a onClick={() => goto('/')} style={{
          fontFamily: 'var(--ff-display)', fontSize: '.95rem',
          textTransform: 'uppercase', letterSpacing: '.06em',
          color: 'var(--retro-ink)', fontWeight: 800, cursor: 'pointer',
        }}>Reverie Pixel Town</a>
        <nav style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {user ? (
            <>
              <NavLink active={route==='/dashboard'} onClick={()=>goto('/dashboard')}>Dashboard</NavLink>
              <NavLink active={route==='/characters'} onClick={()=>goto('/characters')}>Characters</NavLink>
              <NavLink active={route==='/explore'} onClick={()=>goto('/explore')}>Explore</NavLink>
              <NavLink active={route==='/invites'} onClick={()=>goto('/invites')} relative badge={pendingInvites}>Invites</NavLink>
              <span style={{ fontFamily: 'var(--ff-display)', fontSize: '.7rem', textTransform: 'uppercase', letterSpacing: '.04em', color: 'var(--fg-1)' }}>{user.username}</span>
              <Button variant="danger" onClick={onLogout}>Logout</Button>
            </>
          ) : (
            <>
              <NavLink active={route==='/login'} onClick={()=>goto('/login')}>Login</NavLink>
              <NavLink active={route==='/register'} onClick={()=>goto('/register')}>Register</NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

Object.assign(window, { Header });
