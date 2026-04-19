Chart.defaults.color = '#666';
Chart.defaults.borderColor = '#e9ecef';
Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
Chart.defaults.font.size = 12;

const COLORS = {
    primary:'#2c6faa', success:'#28a745', warning:'#f0ad4e',
    danger:'#dc3545', info:'#17a2b8', purple:'#6f42c1', orange:'#fd7e14',
};

const PROTO = {1:'ICMP', 6:'TCP', 17:'UDP'};
function protoName(n) { return PROTO[n] || 'Протокол '+n; }

function fmtBytes(b) {
    if (!b) return '0 Б';
    const k = 1024, s = ['Б','КБ','МБ','ГБ','ТБ'];
    const i = Math.floor(Math.log(b) / Math.log(k));
    return (b / Math.pow(k, i)).toFixed(1) + ' ' + s[i];
}
