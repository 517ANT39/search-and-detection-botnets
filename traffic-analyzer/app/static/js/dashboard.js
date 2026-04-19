let tlChart=null, protoChart=null, talkChart=null, hostChart=null;

async function refresh() {
    const min = document.getElementById('time-range').value;
    const iv = min > 360 ? 300 : 60;

    try {
        const [smR, alR] = await Promise.all([
            fetch('/api/dashboard/summary?minutes='+min),
            fetch('/api/dashboard/alerts-summary'),
        ]);
        const sm = await smR.json(), al = await alR.json();
        let tP=0, tB=0;
        sm.forEach(r=>{tP+=r.total_packets; tB+=r.total_bytes;});
        document.getElementById('card-packets').textContent = tP.toLocaleString('ru-RU');
        document.getElementById('card-bytes').textContent = fmtBytes(tB);
        document.getElementById('card-alerts').textContent = al.unresolved;

        if(hostChart) hostChart.destroy();
        hostChart = new Chart(document.getElementById('chart-hosts'), {
            type:'bar',
            {
                labels:sm.map(r=>(r.host_id||'').substring(0,8)+'…'),
                datasets:[
                    {label:'Входящий', sm.map(r=>r.ingress_bytes), backgroundColor:COLORS.primary},
                    {label:'Исходящий', sm.map(r=>r.egress_bytes), backgroundColor:COLORS.warning},
                ]
            },
            options:{responsive:true, scales:{y:{beginAtZero:true}}}
        });
    } catch(e) { console.error('summary',e); }

    try {
        const r = await fetch(`/api/dashboard/timeline?minutes=${min}&interval=${iv}`);
        const d = await r.json();
        if(tlChart) tlChart.destroy();
        tlChart = new Chart(document.getElementById('chart-timeline'), {
            type:'line',
            {
                labels:d.map(r=>new Date(r.ts).toLocaleTimeString('ru-RU')),
                datasets:[{
                    label:'Пакеты', d.map(r=>r.packets),
                    borderColor:COLORS.primary, fill:true,
                    backgroundColor:'rgba(44,111,170,0.06)', tension:0.3,
                }]
            },
            options:{responsive:true, interaction:{intersect:false,mode:'index'}, scales:{y:{beginAtZero:true}}}
        });
    } catch(e) { console.error('timeline',e); }

    try {
        const r = await fetch('/api/dashboard/protocols?minutes='+min);
        const d = await r.json();
        const pColors=[COLORS.primary,COLORS.success,COLORS.warning,COLORS.danger,COLORS.purple,COLORS.orange];
        if(protoChart) protoChart.destroy();
        protoChart = new Chart(document.getElementById('chart-protocols'), {
            type:'doughnut',
            {
                labels:d.map(r=>protoName(r.protocol)),
                datasets:[{d.map(r=>r.packets), backgroundColor:pColors.slice(0,d.length)}]
            },
            options:{responsive:true, plugins:{legend:{position:'bottom'}}}
        });
    } catch(e) { console.error('protocols',e); }

    try {
        const r = await fetch(`/api/dashboard/top-talkers?minutes=${min}&limit=10`);
        const d = await r.json();
        if(talkChart) talkChart.destroy();
        talkChart = new Chart(document.getElementById('chart-talkers'), {
            type:'bar',
            {
                labels:d.map(r=>r.src+' → '+r.dst),
                datasets:[{label:'Байт', d.map(r=>r.bytes), backgroundColor:COLORS.success}]
            },
            options:{indexAxis:'y', responsive:true, scales:{x:{beginAtZero:true}}}
        });
    } catch(e) { console.error('talkers',e); }
}

document.getElementById('time-range').addEventListener('change', refresh);
document.getElementById('btn-refresh').addEventListener('click', refresh);
refresh();
setInterval(refresh, 30000);
