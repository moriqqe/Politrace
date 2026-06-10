/* Analytical dashboard — six Chart.js views + live posts table. */
applyChartTheme();
const charts = {};

function destroy(k){ if(charts[k]){ charts[k].destroy(); delete charts[k]; } }

/* ---- KPI cards ---- */
async function loadKpis(){
  const k = await api('/api/analytical/kpis');
  const avg = k.avg_sentiment ?? 0;
  const avgCls = avg > 0.05 ? 'pos' : (avg < -0.05 ? 'neg' : 'neu');
  document.getElementById('kpis').innerHTML = `
    <div class="kpi"><div class="label">Total posts</div><div class="value">${fmt(k.total_posts)}</div>
      <div class="sub">${fmt(k.channels)} channels</div></div>
    <div class="kpi"><div class="label">Avg sentiment</div><div class="value ${avgCls}">${avg.toFixed(3)}</div>
      <div class="sub">VADER compound</div></div>
    <div class="kpi"><div class="label">Negative share</div><div class="value neg">${k.neg_pct}%</div>
      <div class="sub">${fmt(k.neg)} negative posts</div></div>
    <div class="kpi"><div class="label">Avg reach</div><div class="value">${fmt(k.avg_views)}</div>
      <div class="sub">views per post</div></div>
    <div class="kpi"><div class="label">Avg length</div><div class="value">${k.avg_words}</div>
      <div class="sub">words per post</div></div>`;
}

/* ---- Time series: bars (volume) + line (sentiment) ---- */
async function loadTimeseries(){
  const d = await api('/api/analytical/timeseries');
  destroy('ts');
  charts.ts = new Chart(document.getElementById('c-timeseries'), {
    data:{ labels:d.map(r=>r.day), datasets:[
      { type:'bar', label:'Posts', data:d.map(r=>r.posts), yAxisID:'y',
        backgroundColor:'rgba(124,92,255,.45)', borderColor:'#7c5cff', borderWidth:1, borderRadius:3 },
      { type:'line', label:'Avg sentiment', data:d.map(r=>r.avg_sentiment), yAxisID:'y1',
        borderColor:'#22d3ee', backgroundColor:'rgba(34,211,238,.15)', tension:.35,
        pointRadius:0, borderWidth:2, fill:true },
    ]},
    options:{ interaction:{mode:'index',intersect:false},
      scales:{
        x:{ ticks:{maxTicksLimit:10}, grid:{display:false} },
        y:{ position:'left', title:{display:true,text:'posts'}, grid:{color:PT.colors.grid} },
        y1:{ position:'right', title:{display:true,text:'sentiment'}, min:-1, max:1,
             grid:{drawOnChartArea:false} },
      }}
  });
}

/* ---- Sentiment doughnut ---- */
async function loadSentiment(){
  const d = await api('/api/analytical/sentiment');
  destroy('sent');
  charts.sent = new Chart(document.getElementById('c-sentiment'), {
    type:'doughnut',
    data:{ labels:d.map(r=>r.label), datasets:[{ data:d.map(r=>r.n),
      backgroundColor:d.map(r=>PT.sentColor(r.label)), borderColor:'#16181f', borderWidth:3 }]},
    options:{ cutout:'62%', plugins:{legend:{position:'bottom'}} }
  });
}

/* ---- Platform comparison stacked bar ---- */
async function loadPlatform(){
  const d = await api('/api/analytical/platform');
  destroy('plat');
  charts.plat = new Chart(document.getElementById('c-platform'), {
    type:'bar',
    data:{ labels:d.map(r=>r.platform), datasets:[
      {label:'Negative',data:d.map(r=>r.negative),backgroundColor:PT.colors.neg,stack:'s'},
      {label:'Neutral', data:d.map(r=>r.neutral), backgroundColor:PT.colors.neu,stack:'s'},
      {label:'Positive',data:d.map(r=>r.positive),backgroundColor:PT.colors.pos,stack:'s'},
    ]},
    options:{ plugins:{legend:{position:'bottom'}},
      scales:{x:{stacked:true,grid:{display:false}},y:{stacked:true,grid:{color:PT.colors.grid}}} }
  });
}

/* ---- Top channels horizontal bar ---- */
async function loadChannels(){
  const d = await api('/api/analytical/channels');
  destroy('chan');
  charts.chan = new Chart(document.getElementById('c-channels'), {
    type:'bar',
    data:{ labels:d.map(r=>r.channel), datasets:[{ label:'Posts', data:d.map(r=>r.posts),
      backgroundColor:'rgba(34,211,238,.5)', borderColor:'#22d3ee', borderWidth:1, borderRadius:4 }]},
    options:{ indexAxis:'y', plugins:{legend:{display:false}},
      scales:{x:{grid:{color:PT.colors.grid}},y:{grid:{display:false}}} }
  });
}

/* ---- Word-count histogram ---- */
async function loadWordcount(){
  const d = await api('/api/analytical/wordcount');
  destroy('wc');
  charts.wc = new Chart(document.getElementById('c-wordcount'), {
    type:'bar',
    data:{ labels:d.map(r=>r.bucket), datasets:[{ label:'Posts', data:d.map(r=>r.n),
      backgroundColor:'rgba(167,139,250,.5)', borderColor:'#a78bfa', borderWidth:1, borderRadius:4 }]},
    options:{ plugins:{legend:{display:false}},
      scales:{x:{grid:{display:false},title:{display:true,text:'words'}},y:{grid:{color:PT.colors.grid}}} }
  });
}

/* ---- Engagement scatter (reach vs interactions) ---- */
async function loadEngagement(){
  const d = await api('/api/analytical/engagement');
  destroy('eng');
  const byLabel = {positive:[],neutral:[],negative:[]};
  d.forEach(r=>{ (byLabel[r.sentiment]||(byLabel[r.sentiment]=[])).push(
    {x:r.views, y:Math.max(r.engagement,0.5)}); });
  charts.eng = new Chart(document.getElementById('c-engagement'), {
    type:'scatter',
    data:{ datasets:Object.keys(byLabel).map(l=>({ label:l, data:byLabel[l],
      backgroundColor:PT.sentColor(l)+'cc', pointRadius:3.5 })) },
    options:{ plugins:{legend:{position:'bottom'}},
      scales:{
        x:{ type:'logarithmic', title:{display:true,text:'views (log)'}, grid:{color:PT.colors.grid} },
        y:{ type:'logarithmic', title:{display:true,text:'interactions (log)'}, grid:{color:PT.colors.grid} },
      }}
  });
}

/* ---- Posts table ---- */
async function loadPosts(){
  const d = await api('/api/analytical/posts');
  const body = document.querySelector('#t-posts tbody');
  if(!d.length){ body.innerHTML = '<tr><td colspan="6" class="loading">No posts match these filters.</td></tr>'; return; }
  const esc = s => (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;');
  body.innerHTML = d.map(r=>{
    const preview = esc(r.preview) + '…';
    const post = r.url
      ? '<a href="'+r.url+'" target="_blank" rel="noopener" class="post-link" title="Open original post">'+preview+' <span class="ext">↗</span></a>'
      : preview;
    return '<tr>'
      + '<td>'+(r.date||'')+'</td>'
      + '<td><span class="badge '+r.platform+'">'+r.platform+'</span></td>'
      + '<td>'+(esc(r.author)||'—')+'</td>'
      + '<td><span class="badge '+(r.sentiment||'neutral')+'">'+(r.sentiment||'—')+'</span></td>'
      + '<td>'+fmt(r.views)+'</td>'
      + '<td>'+post+'</td>'
      + '</tr>';
  }).join('');
}

function refreshAll(){
  loadKpis(); loadTimeseries(); loadSentiment(); loadPlatform();
  loadChannels(); loadWordcount(); loadEngagement(); loadPosts();
}

initFilters(refreshAll).then(refreshAll);
