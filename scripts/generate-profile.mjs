import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
const rows = JSON.parse(readFileSync(root+'data/portrait.json', 'utf8'));
const esc = s => s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const style = '<style>text{font-family:Consolas,monospace}.reveal{animation:appear .6s both}@keyframes appear{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}@media(prefers-reduced-motion:reduce){.reveal{animation:none}}</style>';
function card(w, title, description, body) {
return '<svg xmlns="http://www.w3.org/2000/svg" width="'+w+'" height="430" viewBox="0 0 '+w+' 430" role="img"><title>'+esc(title)+'</title><desc>'+esc(description)+'</desc>'+style+'<rect x="1" y="1" width="'+(w-2)+'" height="428" rx="14" fill="#0d1117" stroke="#303b49"/><path d="M1 48H'+(w-1)+'" stroke="#303b49"/><circle cx="23" cy="25" r="5" fill="#ff6b6b"/><circle cx="42" cy="25" r="5" fill="#f2c76c"/><circle cx="61" cy="25" r="5" fill="#63d6ab"/><text x="83" y="30" font-size="12" fill="#9aaabe">'+esc(title)+'</text>'+body+'</svg>\n';
}
const portrait = rows.map((r,i)=>'<text class="reveal" style="animation-delay:'+(i*.028).toFixed(3)+'s" xml:space="preserve" x="17" y="'+(74+i*6.9).toFixed(1)+'" font-size="7.25" fill="#c4d2dc">'+esc(r)+'</text>').join('');
mkdirSync(root+'assets',{recursive:true});
writeFileSync(root+'assets/portrait.svg', card(340,'francisco / avatar','Retrato ASCII de Francisco Junior, convertido da foto pública do GitHub.',portrait+'<text x="22" y="401" font-size="12" fill="#63d6ab">francisco@github:~$ whoami</text>'));
const lines=[
['FRANCISCO JUNIOR','#e6edf3',26,88],
['Infraestrutura • Automação','#63d6ab',17,119],
['Cloud • DevOps • Observabilidade','#63d6ab',15,145],
['ATUAÇÃO     Windows Server / Linux','#c4d2dc',13,191],
['AUTOMAÇÃO   PowerShell / Bash / Graph','#c4d2dc',13,221],
['MONITORAR   Grafana / Zabbix / SQL','#c4d2dc',13,251],
['LABS        Terraform / Azure / K3s','#c4d2dc',13,281],
['FORMAÇÃO    Engenharia de Software','#c4d2dc',13,311],
['FOCO        Operações confiáveis','#c4d2dc',13,341],
['Documentar. Automatizar. Evoluir.','#9aaabe',13,401]
];
const body=lines.map(([t,c,s,y],i)=>'<text class="reveal" style="animation-delay:'+(i*.1).toFixed(1)+'s" x="24" y="'+y+'" fill="'+c+'" font-size="'+s+'">'+esc(t)+'</text>').join('');
writeFileSync(root+'assets/info-card.svg',card(500,'profile.conf','Perfil de Infraestrutura, automação e observabilidade; projetos de Cloud e DevOps.',body));
console.log('Generated portrait.svg and info-card.svg');

