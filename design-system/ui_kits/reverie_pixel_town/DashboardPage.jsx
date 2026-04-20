const { useState } = React;

function DashboardPage({ user, sims, chars, goto, onObserve }) {
  return (
    <main style={{ maxWidth:'76rem', margin:'0 auto', padding:'2rem 1rem 2.5rem' }}>
      <Panel style={{ padding:'2rem', marginBottom:24 }}>
        <h2 style={{ fontFamily:'var(--ff-display)', fontSize:'clamp(1.3rem,3vw,2rem)', textTransform:'uppercase', letterSpacing:'.04em', margin:'0 0 10px' }}>Dashboard</h2>
        <p style={{ fontSize:'.95rem', color:'var(--fg-2)', margin:0, lineHeight:1.7 }}>Simple flow: create a simulation, add characters, then observe behavior.</p>
      </Panel>

      <Panel style={{ marginBottom:24 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
          <h3 style={{ fontFamily:'var(--ff-display)', fontSize:'1.05rem', textTransform:'uppercase', letterSpacing:'.04em', margin:0 }}>My simulations</h3>
          <Button variant="primary" onClick={()=>goto('/simulations/new')}>Create simulation</Button>
        </div>
        {sims.length === 0 ? (
          <EmptyState>No simulations yet. Create your first simulation!</EmptyState>
        ) : (
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(280px, 1fr))', gap:16 }}>
            {sims.map(s => (
              <div key={s.id} style={{ background:'var(--bg-surface)', border:'3px solid var(--retro-orange)', boxShadow:'4px 4px 0 var(--retro-shadow)', padding:'1.1rem' }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8, gap:8 }}>
                  <h4 style={{ fontFamily:'var(--ff-display)', fontSize:'.85rem', textTransform:'uppercase', letterSpacing:'.04em', margin:0, wordBreak:'break-word' }}>{s.name}</h4>
                  <StatusBadge status={s.status} />
                </div>
                <div style={{ fontSize:'.72rem', color:'var(--fg-3)', marginBottom:4 }}>Map: {s.map}</div>
                <div style={{ fontSize:'.72rem', color:'var(--fg-3)', marginBottom:12 }}>Characters: {s.charCount} · Step: {s.step}</div>
                <div style={{ display:'flex', gap:14 }}>
                  <Link onClick={()=>onObserve(s)}>Observe</Link>
                  <Link>Settings</Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
          <h3 style={{ fontFamily:'var(--ff-display)', fontSize:'1.05rem', textTransform:'uppercase', letterSpacing:'.04em', margin:0 }}>My characters</h3>
          <Button variant="primary" onClick={()=>goto('/characters/new')}>Create character</Button>
        </div>
        {chars.length === 0 ? (
          <EmptyState>No characters yet. Create your first character!</EmptyState>
        ) : (
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))', gap:16 }}>
            {chars.map(c => (
              <div key={c.id} style={{ background:'var(--bg-surface)', border:'3px solid var(--retro-orange)', boxShadow:'4px 4px 0 var(--retro-shadow)', padding:'1rem', display:'flex', gap:12, alignItems:'center' }}>
                <img src={`../../assets/portraits/${c.portrait}.png`} style={{ width:48, height:48, imageRendering:'pixelated', border:'2px solid var(--retro-ink)', background:'#fffdf7', flex:'none' }}/>
                <div style={{ minWidth:0 }}>
                  <h4 style={{ fontFamily:'var(--ff-display)', fontSize:'.78rem', textTransform:'uppercase', letterSpacing:'.03em', margin:'0 0 4px', wordBreak:'break-word' }}>{c.name}</h4>
                  <div style={{ fontSize:'.68rem', color:'var(--fg-3)' }}>Age: {c.age}</div>
                  <div style={{ fontSize:'.68rem', color: c.status==='In simulation' ? '#2a5a1a' : 'var(--fg-3)', fontWeight:800, marginTop:2 }}>{c.status}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </main>
  );
}

Object.assign(window, { DashboardPage });
