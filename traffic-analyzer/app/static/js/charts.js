Chart.defaults.color = '#ccc';
Chart.defaults.borderColor = '#444';

const COLORS = {
    blue:'#0dcaf0', green:'#198754', yellow:'#ffc107',
    red:'#dc3545', purple:'#6f42c1', orange:'#fd7e14',
};

const PROTO = {1:'ICMP', 6:'TCP', 17:'UDP'};
function protoName(n){ return PROTO[n] || 'Proto '+n; }

function fmtBytes(b){
    if(!b) return '0 B';
    const k=1024, s=['B','KB','MB','GB','TB'];
    const i=Math.floor(Math.log(b)/Math.log(k));
    return (b/Math.pow(k,i)).toFixed(2)+' '+s[i];
}
