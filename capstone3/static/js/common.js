/* Shared helpers for both dashboards: filter bar state + fetch + chart theme. */

const PT = {
  colors: {
    accent:'#7c5cff', accent2:'#22d3ee',
    leader:'#a78bfa', hotspot:'#22d3ee',
    pos:'#34d399', neu:'#fbbf24', neg:'#f87171',
    grid:'rgba(255,255,255,.06)', tick:'#8b90a3',
  },
  sentColor(label){
    return {positive:this.colors.pos, neutral:this.colors.neu, negative:this.colors.neg}[label] || '#6b7280';
  },
};

/* Read the global filter bar into a query string. */
function filterParams(extra = {}){
  const p = new URLSearchParams();
  const g = id => (document.getElementById(id) || {}).value;
  const platform = g('f-platform'); if(platform && platform !== 'all') p.set('platform', platform);
  const sentiment = g('f-sentiment'); if(sentiment && sentiment !== 'all') p.set('sentiment', sentiment);
  const start = g('f-start'); if(start) p.set('start', start);
  const end = g('f-end'); if(end) p.set('end', end);
  const q = g('f-search'); if(q) p.set('q', q.trim());
  for(const k in extra) if(extra[k] !== undefined && extra[k] !== null) p.set(k, extra[k]);
  return p.toString();
}

async function api(path, extra = {}){
  const qs = filterParams(extra);
  const res = await fetch(path + (qs ? '?' + qs : ''));
  if(!res.ok) throw new Error(path + ' -> ' + res.status);
  return res.json();
}

/* Populate platform dropdown + date bounds from /api/filters. */
async function initFilters(onApply){
  let opts = {};
  try { opts = await fetch('/api/filters').then(r => r.json()); } catch(e){}
  const start = document.getElementById('f-start');
  const end = document.getElementById('f-end');
  if(start && opts.date_min) start.value = (opts.date_min||'').slice(0,10);
  if(end && opts.date_max) end.value = (opts.date_max||'').slice(0,10);

  document.getElementById('f-apply')?.addEventListener('click', onApply);
  document.getElementById('f-reset')?.addEventListener('click', () => {
    ['f-platform','f-sentiment'].forEach(id => { const el=document.getElementById(id); if(el) el.value='all'; });
    const s=document.getElementById('f-search'); if(s) s.value='';
    if(start && opts.date_min) start.value=(opts.date_min||'').slice(0,10);
    if(end && opts.date_max) end.value=(opts.date_max||'').slice(0,10);
    onApply();
  });
  document.getElementById('f-search')?.addEventListener('keydown', e => { if(e.key==='Enter') onApply(); });
  ['f-platform','f-sentiment'].forEach(id =>
    document.getElementById(id)?.addEventListener('change', onApply));
}

/* Global Chart.js dark defaults. */
function applyChartTheme(){
  if(!window.Chart) return;
  Chart.defaults.color = PT.colors.tick;
  Chart.defaults.font.family = 'Inter, sans-serif';
  Chart.defaults.borderColor = PT.colors.grid;
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(20,22,30,.97)';
  Chart.defaults.plugins.tooltip.borderColor = '#272b38';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.maintainAspectRatio = false;
}

const fmt = n => (n==null ? '—' : Number(n).toLocaleString());
