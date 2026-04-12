async function loadHosts(){
    const r=await fetch('/api/hosts');
    const hosts=await r.json();
    const tb=document.querySelector('#hosts-table tbody');
    tb.innerHTML='';
    hosts.forEach(h=>{
        const ifaces=Array.isArray(h.interfaces)?h.interfaces.join(', '):String(h.interfaces||'');
        tb.innerHTML+=`<tr>
            <td><code title=&quot;${h.host_id}&quot;>${(h.host_id||'').substring(0,12)}…</code></td>
            <td>${h.hostname||'—'}</td>
            <td>${h.os||''} / ${h.arch||''}</td>
            <td>${h.kernel_version||''}</td>
            <td><small>${ifaces}</small></td>
            <td>${h.boot_time||'—'}</td>
            <td>${h.registered_at||'—'}</td>
        </tr>`;
    });
    if(!hosts.length) tb.innerHTML='<tr><td colspan=&quot;7&quot; class=&quot;text-center text-muted&quot;>No hosts</td></tr>';
}
loadHosts(); setInterval(loadHosts,60000);
