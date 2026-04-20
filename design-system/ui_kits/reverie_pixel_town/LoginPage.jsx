const { useState } = React;

function LoginPage({ goto, onLogin }) {
  const [u, setU] = useState('');
  const [p, setP] = useState('');
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = (e) => {
    e.preventDefault();
    setErr(null);
    if (!u || !p) { setErr('Fill in both fields'); return; }
    setLoading(true);
    setTimeout(() => { setLoading(false); onLogin({ username: u }); }, 500);
  };

  return (
    <div style={{ minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center', padding:'2.5rem 1rem' }}>
      <Panel style={{ padding:'2rem', width:'100%', maxWidth:'30rem' }}>
        <h2 style={{ fontFamily:'var(--ff-display)', fontSize:'1.5rem', textTransform:'uppercase', letterSpacing:'.04em', margin:'0 0 8px' }}>Sign in</h2>
        <p style={{ fontSize:'.8rem', color:'var(--fg-2)', lineHeight:1.6, margin:'0 0 20px' }}>Step 1: Sign in. Step 2: create simulation. Step 3: watch your pixel town.</p>
        <form onSubmit={submit} style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <Input label="Username" required value={u} onChange={setU} placeholder="your_username" />
          <Input label="Password" required type="password" value={p} onChange={setP} placeholder="••••••••" />
          {err && <div style={{ color:'var(--retro-rose)', fontSize:'.8rem' }}>{err}</div>}
          <Button variant="primary" type="submit" disabled={loading} style={{ width:'100%' }}>
            {loading ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
        <div style={{ marginTop:24 }}>
          <div style={{ position:'relative', textAlign:'center', marginBottom:16 }}>
            <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center' }}>
              <div style={{ width:'100%', borderTop:'2px solid var(--fg-4)' }} />
            </div>
            <span style={{ position:'relative', background:'var(--bg-surface)', padding:'0 10px', fontSize:'.72rem', color:'var(--fg-3)', fontFamily:'var(--ff-display)', textTransform:'uppercase', letterSpacing:'.04em' }}>Or continue with</span>
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
            <Button variant="ghost" style={{ width:'100%', display:'inline-flex', alignItems:'center', justifyContent:'center', gap:8 }}>
              <svg width="20" height="20" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M23.745 12.27c0-.79-.07-1.54-.19-2.27h-11.3v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82z"/>
                <path fill="#34A853" d="M12.255 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96h-3.98v3.09C3.515 21.3 7.615 24 12.255 24z"/>
                <path fill="#FBBC05" d="M5.525 14.29c-.25-.72-.38-1.49-.38-2.29s.14-1.57.38-2.29V6.62h-3.98a11.86 11.86 0 0 0 0 10.76l3.98-3.09z"/>
                <path fill="#EA4335" d="M12.255 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C18.205 1.19 15.495 0 12.255 0c-4.64 0-8.74 2.7-10.71 6.62l3.98 3.09c.95-2.85 3.6-4.96 6.73-4.96z"/>
              </svg>
              Continue with Google
            </Button>
            <Button variant="ghost" style={{ width:'100%', display:'inline-flex', alignItems:'center', justifyContent:'center', gap:8 }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12"/>
              </svg>
              Continue with GitHub
            </Button>
          </div>
        </div>
        <p style={{ marginTop:16, textAlign:'center', fontSize:'.8rem', color:'var(--fg-2)' }}>
          Don't have an account?{' '}
          <a onClick={()=>goto('/register')} style={{ color:'var(--retro-rose)', textDecoration:'underline', fontWeight:800, cursor:'pointer' }}>Create account</a>
        </p>
      </Panel>
    </div>
  );
}

Object.assign(window, { LoginPage });
