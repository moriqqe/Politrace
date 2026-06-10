/* Strategic dashboard — Obsidian-style D3 co-mention network + supporting views. */
applyChartTheme();

let curType = 'all';
let minWeight = 40;
const tip = document.getElementById('tooltip');

/* ===================== KPI cards ===================== */
async function loadKpis(){
  const k = await api('/api/strategic/kpis');
  const avg = k.avg_sentiment ?? 0;
  const avgCls = avg > 0.05 ? 'pos' : (avg < -0.05 ? 'neg' : 'neu');
  document.getElementById('kpis').innerHTML = `
    <div class="kpi"><div class="label">Posts in scope</div><div class="value">${fmt(k.total_posts)}</div>
      <div class="sub">feeding the graph</div></div>
    <div class="kpi"><div class="label">Leaders tracked</div><div class="value" style="color:var(--leader)">${fmt(k.leaders)}</div>
      <div class="sub">political figures</div></div>
    <div class="kpi"><div class="label">Hotspots tracked</div><div class="value" style="color:var(--hotspot)">${fmt(k.hotspots)}</div>
      <div class="sub">regions & flashpoints</div></div>
    <div class="kpi"><div class="label">Entity mentions</div><div class="value">${fmt(k.mentions)}</div>
      <div class="sub">total references</div></div>
    <div class="kpi"><div class="label">Overall tone</div><div class="value ${avgCls}">${avg.toFixed(3)}</div>
      <div class="sub">avg VADER score</div></div>`;
}

/* ===================== Network graph ===================== */
const svgEl = document.getElementById('graph');
let svg, gZoom, gLink, gNode, gLabel, sim, zoomBehavior;

function setupSvg(){
  const w = svgEl.clientWidth, h = svgEl.clientHeight;
  svg = d3.select(svgEl).attr('viewBox', [0,0,w,h]);
  svg.selectAll('*').remove();

  // soft glow filter for the Obsidian look
  const defs = svg.append('defs');
  const f = defs.append('filter').attr('id','glow').attr('x','-60%').attr('y','-60%')
    .attr('width','220%').attr('height','220%');
  f.append('feGaussianBlur').attr('stdDeviation','3.2').attr('result','b');
  const m = f.append('feMerge');
  m.append('feMergeNode').attr('in','b');
  m.append('feMergeNode').attr('in','SourceGraphic');

  gZoom = svg.append('g');
  gLink = gZoom.append('g').attr('stroke-linecap','round');
  gNode = gZoom.append('g');
  gLabel = gZoom.append('g');

  zoomBehavior = d3.zoom().scaleExtent([0.3, 4]).on('zoom', e => gZoom.attr('transform', e.transform));
  svg.call(zoomBehavior);
}

const sentRing = s => s == null ? '#6b7280' : (s > 0.05 ? PT.colors.pos : (s < -0.05 ? PT.colors.neg : PT.colors.neu));
const typeFill = t => t === 'leader' ? PT.colors.leader : PT.colors.hotspot;

async function loadNetwork(){
  const data = await api('/api/strategic/network', {min_weight:minWeight, type:curType});
  const w = svgEl.clientWidth, h = svgEl.clientHeight;
  if(!svg) setupSvg();

  document.getElementById('g-hint').textContent =
    `${data.nodes.length} entities · ${data.links.length} connections shown`;

  const mMax = d3.max(data.nodes, d=>d.mentions) || 1;
  const rScale = d3.scaleSqrt().domain([1, mMax]).range([7, 34]);
  const wMax = d3.max(data.links, d=>d.weight) || 1;
  const wScale = d3.scaleSqrt().domain([1, wMax]).range([1, 9]);

  // deep-copy so the sim can mutate
  const nodes = data.nodes.map(d=>({...d}));
  const links = data.links.map(d=>({...d}));

  if(sim) sim.stop();
  sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d=>d.id).distance(l=>120 - wScale(l.weight)*4).strength(l=>Math.min(1, l.weight/wMax+0.1)))
    .force('charge', d3.forceManyBody().strength(-340))
    .force('center', d3.forceCenter(w/2, h/2))
    .force('collide', d3.forceCollide().radius(d=>rScale(d.mentions)+6))
    .force('x', d3.forceX(w/2).strength(0.04))
    .force('y', d3.forceY(h/2).strength(0.04));

  // links
  const link = gLink.selectAll('line').data(links, d=>d.source.id+'-'+d.target.id);
  link.exit().remove();
  const linkEnter = link.enter().append('line')
    .attr('stroke', '#4a4f63').attr('stroke-opacity', .35)
    .attr('stroke-width', d=>wScale(d.weight));
  const allLinks = linkEnter.merge(link);

  // nodes
  const node = gNode.selectAll('circle').data(nodes, d=>d.id);
  node.exit().remove();
  const nodeEnter = node.enter().append('circle')
    .attr('r', d=>rScale(d.mentions))
    .attr('fill', d=>typeFill(d.type))
    .attr('stroke', d=>sentRing(d.avg_sentiment))
    .attr('stroke-width', 2.5)
    .attr('filter','url(#glow)')
    .style('cursor','pointer')
    .call(drag());
  const allNodes = nodeEnter.merge(node);

  // labels (always show the biggest, others on hover)
  const label = gLabel.selectAll('text').data(nodes, d=>d.id);
  label.exit().remove();
  const labelEnter = label.enter().append('text')
    .attr('class','node-label').attr('text-anchor','middle').attr('dy', d=>-rScale(d.mentions)-5)
    .text(d=>d.name);
  const allLabels = labelEnter.merge(label)
    .style('opacity', d=>d.mentions > mMax*0.18 ? 1 : 0);

  // adjacency for hover spotlight
  const adj = new Map();
  links.forEach(l=>{
    const s = l.source.id ?? l.source, t = l.target.id ?? l.target;
    (adj.get(s)||adj.set(s,new Set()).get(s)).add(t);
    (adj.get(t)||adj.set(t,new Set()).get(t)).add(s);
  });
  let pinned = null;

  function spotlight(d){
    const keep = new Set([d.id, ...(adj.get(d.id)||[])]);
    allNodes.style('opacity', n=>keep.has(n.id)?1:.12);
    allLabels.style('opacity', n=>keep.has(n.id)?1:.05);
    allLinks.attr('stroke-opacity', l=>(l.source.id===d.id||l.target.id===d.id)?.85:.04)
            .attr('stroke', l=>(l.source.id===d.id||l.target.id===d.id)?'#9aa0b8':'#4a4f63');
  }
  function clearSpot(){
    allNodes.style('opacity',1);
    allLabels.style('opacity', n=>n.mentions > mMax*0.18 ? 1 : 0);
    allLinks.attr('stroke-opacity',.35).attr('stroke','#4a4f63');
  }

  allNodes
    .on('mouseover',(e,d)=>{ if(!pinned) spotlight(d);
      tip.style.opacity=1; tip.innerHTML =
        `<b>${d.name}</b> <span class="badge ${d.type==='leader'?'twitter':'telegram'}">${d.type}</span>
         <div class="meta">${fmt(d.mentions)} mentions · tone ${(d.avg_sentiment??0).toFixed(2)}</div>`; })
    .on('mousemove',e=>{ tip.style.left=(e.clientX+14)+'px'; tip.style.top=(e.clientY+14)+'px'; })
    .on('mouseout',()=>{ tip.style.opacity=0; if(!pinned) clearSpot(); })
    .on('click',(e,d)=>{ if(pinned===d.id){ pinned=null; clearSpot(); } else { pinned=d.id; spotlight(d); } e.stopPropagation(); });
  svg.on('click',()=>{ pinned=null; clearSpot(); });

  sim.on('tick', ()=>{
    allLinks.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
            .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
    allNodes.attr('cx',d=>d.x).attr('cy',d=>d.y);
    allLabels.attr('x',d=>d.x).attr('y',d=>d.y);
  });
  sim.alpha(1).restart();
}

function drag(){
  return d3.drag()
    .on('start',(e,d)=>{ if(!e.active) sim.alphaTarget(.3).restart(); d.fx=d.x; d.fy=d.y; })
    .on('drag',(e,d)=>{ d.fx=e.x; d.fy=e.y; })
    .on('end',(e,d)=>{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; });
}

/* ===================== Topic cloud ===================== */
async function loadCloud(){
  const d = await api('/api/strategic/entities', {type:curType, });
  const max = d3.max(d, x=>x.mentions) || 1;
  const el = document.getElementById('cloud');
  el.innerHTML = d.map(x=>{
    const size = 12 + 18*Math.sqrt(x.mentions/max);
    return `<span class="tag ${x.type}" style="font-size:${size.toFixed(0)}px"
      title="${fmt(x.mentions)} mentions">${x.name}</span>`;
  }).join('');
}

/* ===================== Entity sentiment diverging bar ===================== */
let entChart;
async function loadEntitySentiment(){
  const d = await api('/api/strategic/entity_sentiment');
  if(entChart) entChart.destroy();
  entChart = new Chart(document.getElementById('c-entsent'), {
    type:'bar',
    data:{ labels:d.map(r=>r.name), datasets:[{ label:'Avg sentiment',
      data:d.map(r=>r.avg_sentiment),
      backgroundColor:d.map(r=>sentRing(r.avg_sentiment)+'cc'),
      borderColor:d.map(r=>sentRing(r.avg_sentiment)), borderWidth:1, borderRadius:4 }]},
    options:{ indexAxis:'y', plugins:{legend:{display:false}},
      scales:{ x:{min:-0.8,max:0.4,grid:{color:PT.colors.grid}}, y:{grid:{display:false}} } }
  });
}

/* ===================== Hotspot leaderboard ===================== */
async function loadHotspots(){
  const d = await api('/api/strategic/hotspots');
  const body = document.querySelector('#t-hot tbody');
  body.innerHTML = d.map((r,i)=>{
    const tone = r.avg_sentiment>0.05?'positive':(r.avg_sentiment<-0.05?'negative':'neutral');
    return `<tr><td>${i+1}</td><td>${r.name}</td><td>${fmt(r.mentions)}</td>
      <td><span class="badge ${tone}">${(r.avg_sentiment??0).toFixed(2)}</span></td></tr>`;
  }).join('');
}

/* ===================== Wiring ===================== */
function refreshAll(){
  loadKpis(); loadNetwork(); loadCloud(); loadEntitySentiment(); loadHotspots();
}

document.getElementById('type-seg').addEventListener('click', e=>{
  const b = e.target.closest('button'); if(!b) return;
  document.querySelectorAll('#type-seg button').forEach(x=>x.classList.remove('active'));
  b.classList.add('active'); curType = b.dataset.type;
  loadNetwork(); loadCloud();
});

let mwTimer;
const mw = document.getElementById('mw');
mw.addEventListener('input', ()=>{
  minWeight = +mw.value; document.getElementById('mw-val').textContent = minWeight;
  clearTimeout(mwTimer); mwTimer = setTimeout(loadNetwork, 220);
});

window.addEventListener('resize', ()=>{ if(svg){ const w=svgEl.clientWidth,h=svgEl.clientHeight;
  svg.attr('viewBox',[0,0,w,h]); sim?.force('center', d3.forceCenter(w/2,h/2)).alpha(.3).restart(); }});

setupSvg();
initFilters(refreshAll).then(refreshAll);
