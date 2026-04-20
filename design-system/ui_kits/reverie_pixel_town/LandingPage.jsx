const { useState } = React;

function LandingPage({ goto }) {
  const [simName, setSimName] = useState('');
  const [forkFrom, setForkFrom] = useState('');

  return (
    <div>
      <header style={{
        background: 'var(--retro-sky)',
        borderBottom: '4px solid var(--retro-orange)',
        boxShadow: '0 6px 0 var(--retro-shadow)',
      }}>
        <div style={{ maxWidth: '76rem', margin: '0 auto', padding: '14px 16px', display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:12 }}>
          <div style={{ fontFamily: 'var(--ff-display)', fontSize: '.95rem', textTransform:'uppercase', letterSpacing:'.06em', fontWeight:800 }}>Reverie Pixel Town</div>
          <nav style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
            <NavLink onClick={()=>goto('/login')}>Sign in</NavLink>
            <NavLink onClick={()=>goto('/register')}>Register</NavLink>
            <NavLink onClick={()=>goto('/dashboard')}>Simulator</NavLink>
            <NavLink onClick={()=>goto('/demo')}>Demo replay</NavLink>
          </nav>
        </div>
      </header>
      <main style={{ maxWidth:'76rem', margin:'0 auto', padding:'2rem 1rem 2.5rem' }}>
        <Panel style={{ padding:'2rem', marginBottom:24 }}>
          <h2 style={{ fontFamily:'var(--ff-display)', fontSize:'clamp(1.3rem,3vw,2rem)', textTransform:'uppercase', letterSpacing:'.04em', margin:'0 0 12px' }}>Pixel-style agent playground</h2>
          <p style={{ fontSize:'.95rem', lineHeight:1.7, color:'var(--fg-2)', maxWidth:'48rem', margin:'0 0 20px' }}>
            Follow three easy steps: create your simulation, drop characters, then watch your town come alive in a retro map view.
          </p>
          <div style={{ border:'3px solid var(--retro-sky)', background:'var(--bg-info-soft)', padding:'1rem', maxWidth:'48rem' }}>
            {[[1,'Sign in and create a simulation from your dashboard.'],[2,'Add or invite characters to your simulation.'],[3,'Open live simulator or replay mode to observe behavior.']].map(([n,t])=>(
              <div key={n} style={{ display:'flex', gap:12, alignItems:'flex-start', marginBottom:10 }}>
                <span style={{ flex:'none', width:26, height:26, display:'inline-flex', alignItems:'center', justifyContent:'center', border:'2px solid var(--retro-ink)', background:'var(--retro-sun)', fontFamily:'var(--ff-display)', fontSize:'.72rem', fontWeight:800 }}>{n}</span>
                <div style={{ fontSize:'.85rem', lineHeight:1.55 }}>{t}</div>
              </div>
            ))}
          </div>
        </Panel>

        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(260px, 1fr))', gap:16, marginBottom:24 }}>
          <Panel style={{ cursor:'pointer' }} onClick={()=>goto('/dashboard')}>
            <h3 style={{ fontFamily:'var(--ff-display)', fontSize:'1.05rem', textTransform:'uppercase', letterSpacing:'.04em', margin:'0 0 8px' }}>Live simulation</h3>
            <p style={{ fontSize:'.78rem', color:'var(--fg-2)', margin:'0 0 12px' }}>Watch agents walk, chat, and plan in real time.</p>
            <Link onClick={()=>goto('/dashboard')}>Open live simulator</Link>
          </Panel>
          <Panel>
            <h3 style={{ fontFamily:'var(--ff-display)', fontSize:'1.05rem', textTransform:'uppercase', letterSpacing:'.04em', margin:'0 0 8px' }}>Demo replay</h3>
            <p style={{ fontSize:'.78rem', color:'var(--fg-2)', margin:'0 0 12px' }}>Replay saved sessions with a timeline scrubber.</p>
            <Link>Open replay viewer</Link>
          </Panel>
        </div>

        <Panel style={{ padding:'2rem' }}>
          <h3 style={{ fontFamily:'var(--ff-display)', fontSize:'1.05rem', textTransform:'uppercase', letterSpacing:'.04em', margin:'0 0 16px' }}>Quick simulation name tester</h3>
          <form onSubmit={e=>{e.preventDefault(); alert(`Creating: ${simName}`);}} style={{ display:'flex', flexDirection:'column', gap:16 }}>
            <Input label="Simulation name" required value={simName} onChange={setSimName} placeholder="my_ville_experiment" />
            <Input label="Fork from (optional)" value={forkFrom} onChange={setForkFrom} placeholder="base_the_ville..." hint="Leave empty to start fresh." />
            <div><Button variant="warm" type="submit">Create simulation</Button></div>
          </form>
        </Panel>
      </main>
    </div>
  );
}

Object.assign(window, { LandingPage });
