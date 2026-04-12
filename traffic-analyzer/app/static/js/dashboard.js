let tlChart=null, protoChart=null, talkChart=null, hostChart=null;

async function refresh(){
    const min=document.getElementById('time-range').value;
    const iv=min>360?300:60;

    // Cards
    const [smR,alR]=await Promise.all([
        fetch('/api/dashboard/summary?minutes='+min),
        fetch('/api/dashboard/alerts-summary'),
    ]);
    const sm=await smR.json(), al=await alR.json();
    let tP=0,tB=0; sm.forEach(r=>{tP+=r.total_packets;tB+=r.total_bytes;});
    document.getElementById('card-packets').textContent=tP.toLocaleString();
    document.getElementById('card-bytes').textContent=fmtBytes(tB);
    document.getElementById('card-alerts').textContent=al.unresolved;
    document.getElementById('card-critical').textContent=al.critical;

    // Host chart
    if(hostChart)hostChart.destroy();
    hostChart=new Chart(document.getElementById('chart-hosts'),{type:'bar',{
        labels:sm.map(r=>(r.host_id||'').substring(0,8)+'…'),
        datasets:[
            {label:'Ingress',sm.map(r=>r.ingress_bytes),backgroundColor:COLORS.blue},
            {label:'Egress',sm.map(r=>r.egress_bytes),backgroundColor:COLORS.yellow},
        ]
    },options:{responsive:true,scales:{y:{beginAtZero:true}}}});

    // Timeline
    let r=await fetch(`/api/dashboard/timeline?minutes=${min}&amp;interval=${iv}`);
    let d=await r.json();
    if(tlChart)tlChart.destroy();
    tlChart=new Chart(document.getElementById('chart-timeline'),{type:'line',{
        labels:d.map(r=>new Date(r.ts).toLocaleTimeString()),
        datasets:[{label:'Packets',d.map(r=>r.packets),borderColor:COLORS.blue,fill:true,backgroundColor:'rgba(13,202,240,0.08)',tension:0.3}]
    },options:{responsive:true,scales:{y:{beginAtZero:true}}}});

    // Protocols
    r=await fetch('/api/dashboard/protocols?minutes='+min); d=await r.json();
    const pColors=[COLORS.blue,COLORS.green,COLORS.yellow,COLORS.red,COLORS.purple,COLORS.orange];
    if(protoChart)protoChart.destroy();
    protoChart=new Chart(document.getElementById('chart-protocols'),{type:'doughnut',{
        labels:d.map(r=>protoName(r.protocol)),
        datasets:[{d.map(r=>r.packets),backgroundColor:pColors.slice(0,d.length)}]
    },options:{responsive:true,plugins:{legend:{position:'bottom'}}}});

    // Top talkers
    r=await fetch(`/api/dashboard/top-talkers?minutes=${min}&amp;limit=10`); d=await r.json();
    if(talkChart)talkChart.destroy();
    talkChart=new Chart(document.getElementById('chart-talkers'),{type:'bar',{
        labels:d.map(r=>r.src+' → '+r.dst),
        datasets:[{label:'Bytes',d.map(r=>r.bytes),backgroundColor:COLORS.green}]
    },options:{indexAxis:'y',responsive:true}});
}

document.getElementById('time-range').addEventListener('change',refresh);
document.getElementById('btn-refresh').addEventListener('click',refresh);
refresh(); setInterval(refresh,30000);
