const { useState } = React;

function CharactersPage({ chars, goto }) {
  return (
    <main style={{ maxWidth:'76rem', margin:'0 auto', padding:'2rem 1rem 2.5rem' }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20, gap:12, flexWrap:'wrap' }}>
        <h2 style={{ fontFamily:'var(--ff-display)', fontSize:'clamp(1.3rem,3vw,2rem)', textTransform:'uppercase', letterSpacing:'.04em', margin:0 }}>My Characters</h2>
        <Button variant="primary" onClick={()=>goto('/characters/new')}>Create character</Button>
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(240px, 1fr))', gap:16 }}>
        {chars.map(c => (
          <div key={c.id} style={{ background:'var(--bg-surface)', border:'3px solid var(--retro-orange)', boxShadow:'6px 6px 0 var(--retro-shadow)', padding:'1.1rem' }}>
            <div style={{ display:'flex', gap:12, alignItems:'center', marginBottom:10 }}>
              <img src={`../../assets/portraits/${c.portrait}.png`} style={{ width:56, height:56, imageRendering:'pixelated', border:'2px solid var(--retro-ink)', background:'#fffdf7', flex:'none' }}/>
              <div style={{ minWidth:0 }}>
                <h3 style={{ fontFamily:'var(--ff-display)', fontSize:'.82rem', textTransform:'uppercase', margin:'0 0 4px', letterSpacing:'.03em' }}>{c.name}</h3>
                <div style={{ fontSize:'.7rem', color:'var(--fg-3)' }}>Age: {c.age}</div>
                <div style={{ fontSize:'.7rem', marginTop:2, color: c.status==='In simulation' ? '#2a5a1a' : 'var(--fg-3)', fontWeight:800 }}>{c.status}</div>
              </div>
            </div>
            <div style={{ display:'flex', gap:14 }}>
              {c.status==='In simulation' ? (
                <span style={{ fontSize:'.7rem', color:'var(--fg-4)', fontFamily:'var(--ff-display)', textTransform:'uppercase' }}>Edit</span>
              ) : <Link>Edit</Link>}
              {c.status==='In simulation' ? (
                <span style={{ fontSize:'.7rem', color:'var(--fg-4)', fontFamily:'var(--ff-display)', textTransform:'uppercase' }}>Delete</span>
              ) : <a style={{ color:'var(--retro-rose)', textDecoration:'underline', fontWeight:800, fontSize:'.72rem', cursor:'pointer', fontFamily:'var(--ff-display)', textTransform:'uppercase' }}>Delete</a>}
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}

Object.assign(window, { CharactersPage });
