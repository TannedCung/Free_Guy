const { useState, useEffect, useRef } = React;

function ObservePage({ sim, goto }) {
  const [speed, setSpeed] = useState(3);
  const [running, setRunning] = useState(true);
  const [step, setStep] = useState(sim?.step ?? 128);
  const [log, setLog] = useState([
    { t:128, a:'Isabella', text:'Heading to the cafe to open up.' },
    { t:128, a:'Klaus',    text:'Finishing my morning routine.' },
    { t:127, a:'Abigail',  text:'Hey Klaus, mind if I join you for coffee?' },
    { t:127, a:'Klaus',    text:'Not at all, Abigail. How are you?' },
    { t:126, a:'Sam',      text:'Taking a walk in the park.' },
  ]);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      setStep(s => s + 1);
    }, 2000 / speed);
    return () => clearInterval(id);
  }, [running, speed]);

  const agents = [
    { name:'Isabella', portrait:'Isabella_Rodriguez', loc:'Hobbs Cafe',   act:'Brewing coffee' },
    { name:'Klaus',    portrait:'Klaus_Mueller',      loc:'Hobbs Cafe',   act:'Reading Adorno' },
    { name:'Abigail',  portrait:'Abigail_Chen',       loc:'Hobbs Cafe',   act:'Sketching' },
    { name:'Maria',    portrait:'Maria_Lopez',        loc:'The Willows',  act:'Writing a poem' },
    { name:'Sam',      portrait:'Sam_Moore',          loc:'Johnson Park', act:'Walking' },
  ];

  return (
    <main style={{ maxWidth:'76rem', margin:'0 auto', padding:'2rem 1rem 2.5rem' }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16, gap:12, flexWrap:'wrap' }}>
        <div>
          <div style={{ fontFamily:'var(--ff-display)', fontSize:'.6rem', textTransform:'uppercase', letterSpacing:'.06em', color:'var(--fg-3)' }}>Simulation</div>
          <h2 style={{ fontFamily:'var(--ff-display)', fontSize:'1.3rem', textTransform:'uppercase', letterSpacing:'.04em', margin:'4px 0 0' }}>{sim?.name || 'my_ville_experiment'}</h2>
        </div>
        <div style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
          <Button variant={running?'warm':'primary'} onClick={()=>setRunning(r=>!r)}>{running ? 'Pause' : 'Resume'}</Button>
          <Button variant="ghost" onClick={()=>{ setStep(s=>s+1); }}>Step +1</Button>
          <Button variant="danger" onClick={()=>goto('/dashboard')}>Exit</Button>
        </div>
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'minmax(0,2fr) minmax(260px,1fr)', gap:16 }}>
        {/* Map canvas stand-in */}
        <Panel compact>
          <div style={{ fontFamily:'var(--ff-display)', fontSize:'.64rem', textTransform:'uppercase', letterSpacing:'.06em', color:'var(--fg-3)', marginBottom:8 }}>The Ville · live</div>
          <div style={{ position:'relative', overflow:'hidden', border:'2px solid var(--retro-ink)' }}>
            <img src="../../assets/cover.png" style={{ width:'100%', display:'block', imageRendering:'pixelated' }}/>
          </div>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginTop:12, flexWrap:'wrap', gap:10 }}>
            <div style={{ fontFamily:'var(--ff-mono)', fontSize:'.75rem', color:'var(--fg-2)' }}>Step {step} · {running?'running':'paused'} · speed ×{speed}</div>
            <div style={{ display:'flex', alignItems:'center', gap:8 }}>
              <span style={{ fontFamily:'var(--ff-display)', fontSize:'.6rem', textTransform:'uppercase', color:'var(--fg-3)' }}>Speed</span>
              {[1,2,3,4,5].map(n => (
                <button key={n} onClick={()=>setSpeed(n)} style={{
                  width:28, height:28, border:'2px solid var(--retro-ink)', cursor:'pointer',
                  background: n===speed ? 'var(--retro-sun)' : '#fff',
                  fontFamily:'var(--ff-display)', fontSize:'.7rem',
                }}>{n}</button>
              ))}
            </div>
          </div>
        </Panel>

        {/* Agents panel */}
        <Panel compact>
          <div style={{ fontFamily:'var(--ff-display)', fontSize:'.64rem', textTransform:'uppercase', letterSpacing:'.06em', color:'var(--fg-3)', marginBottom:10 }}>Agents · {agents.length}</div>
          <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
            {agents.map(a => (
              <div key={a.name} style={{ display:'flex', gap:10, alignItems:'center', padding:'8px', border:'2px solid var(--retro-ink)', background:'#fffdf7' }}>
                <img src={`../../assets/portraits/${a.portrait}.png`} style={{ width:40, height:40, imageRendering:'pixelated', flex:'none', background:'#fff' }}/>
                <div style={{ minWidth:0 }}>
                  <div style={{ fontFamily:'var(--ff-display)', fontSize:'.7rem', textTransform:'uppercase', letterSpacing:'.03em' }}>{a.name}</div>
                  <div style={{ fontFamily:'var(--ff-mono)', fontSize:'.68rem', color:'var(--fg-3)', marginTop:2 }}>@ {a.loc}</div>
                  <div style={{ fontFamily:'var(--ff-mono)', fontSize:'.68rem', color:'var(--fg-2)' }}>{a.act}</div>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* Dialog log */}
      <Panel style={{ marginTop:16 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10 }}>
          <div style={{ fontFamily:'var(--ff-display)', fontSize:'.72rem', textTransform:'uppercase', letterSpacing:'.06em' }}>Dialog log</div>
          <div style={{ fontFamily:'var(--ff-mono)', fontSize:'.68rem', color:'var(--fg-3)' }}>tail -f · sse stream</div>
        </div>
        <div style={{ border:'2px solid var(--retro-ink)', background:'#fffdf7', padding:'10px 12px', maxHeight:220, overflow:'auto', fontFamily:"'VT323',monospace", fontSize:'1.05rem', lineHeight:1.35 }}>
          {log.map((l, i) => (
            <div key={i}>
              <span style={{ color:'var(--fg-3)' }}>[step {l.t}] </span>
              <span style={{ color:'var(--retro-rose)', fontWeight:700 }}>[{l.a}]:</span>{' '}
              <span>{l.text}</span>
            </div>
          ))}
        </div>
      </Panel>
    </main>
  );
}

Object.assign(window, { ObservePage });
