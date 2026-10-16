const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const brl = value => Number(value).toLocaleString('pt-BR', {style:'currency',currency:'BRL'});
const localDate = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
const dateBR = value => value ? value.split('-').reverse().join('/') : '—';
let accessToken = null; // Memory only: a reload requires login.
let user, members=[], accounts=[], categories=[], entries=[], dashboard={}, page='dashboard', editing=null, register=false, charts=[];
let toastTimer;
function notify(message) { $('#toast').textContent=message; $('#toast').classList.add('show'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),6000); }
async function api(path, options={}) {
  const response=await fetch('/api'+path,{...options,headers:{'Content-Type':'application/json',...(accessToken?{Authorization:'Bearer '+accessToken}:{}),...options.headers}});
  if(!response.ok) { let data; try {data=await response.json();} catch {data={detail:'Falha de comunicação'};} if(response.status===401 && accessToken) logout(); throw new Error(Array.isArray(data.detail)?data.detail.map(e=>`${e.loc.at(-1)}: ${e.msg}`).join('; '):data.detail||'Operação não concluída'); }
  return response.status===204?null:response.json();
}
const send=(path,method,data)=>api(path,{method,body:JSON.stringify(data)});
function logout(){accessToken=null;$('#app').hidden=true;$('#auth').hidden=false;$('#auth-form').reset();charts.forEach(c=>c.destroy());charts=[];}
function options(list, selected) {return list.map(o=>`<option value="${o.id}" ${String(selected)===String(o.id)?'selected':''}>${escapeHtml(o.name)}</option>`).join('');}
function params() {const p=new URLSearchParams({month:$('#month').value}); [['owner_id','#filter-owner'],['category_id','#filter-category'],['account_id','#filter-account']].forEach(([key,s])=>{if($(s).value)p.set(key,$(s).value);});return '?'+p;}
async function refresh() {
 [members,accounts,categories]=await Promise.all([api('/members'),api('/accounts'),api('/categories')]);
 [['#filter-owner',members,'Todos'],['#filter-category',categories,'Todas'],['#filter-account',accounts,'Todas']].forEach(([s,list,label])=>{const value=$(s).value;$(s).innerHTML=`<option value="">${label}</option>`+options(list,value);});
 [entries,dashboard]=await Promise.all([api('/entries'+params()),api('/dashboard'+params())]);
 render();
}
function stat(label,value,note='',featured=false){return `<div class="stat ${featured?'featured':''}"><div class="stat-label">${escapeHtml(label)}</div><strong>${escapeHtml(value)}</strong><small>${escapeHtml(note)}</small></div>`;}
function table(list,actions=false) {
 if(!list.length)return '<div class="empty">Nenhum lançamento por aqui. Comece adicionando uma receita ou despesa.</div>';
 return `<div class="table-wrap"><table><thead><tr><th>DESCRIÇÃO / CATEGORIA</th><th>RESPONSÁVEL</th><th>VENCIMENTO</th><th>SITUAÇÃO</th><th>VALOR</th>${actions?'<th>AÇÕES</th>':''}</tr></thead><tbody>`+list.map(e=>{const overdue=e.kind==='expense' && !e.settled_date && e.due_date<localDate();return `<tr><td><b>${escapeHtml(e.description)}</b><small>${escapeHtml(categories.find(c=>c.id===e.category_id)?.name)}${e.shared?' · Compartilhada':''}${e.private?' · Privada':''}</small></td><td>${escapeHtml(members.find(m=>m.id===e.owner_id)?.name)}</td><td>${dateBR(e.due_date)}</td><td><span class="badge ${e.settled_date?'':overdue?'overdue':'pending'}">${e.settled_date?(e.kind==='income'?'Recebida':'Paga'):overdue?'Vencida':e.kind==='income'?'Prevista':'Pendente'}</span></td><td class="${e.kind==='income'?'positive':'negative'}">${e.kind==='income'?'+':'−'} ${brl(e.amount)}</td>${actions?`<td>${user.role==='admin'||e.owner_id===user.id?`<button data-edit="${e.id}">Editar</button><button data-delete="${e.id}">Cancelar</button>`:'—'}</td>`:''}</tr>`;}).join('')+'</tbody></table></div>';
}
function render(){
 const d=dashboard;
 $('#stats').innerHTML=stat('Receitas do mês',brl(d.income),'Recebidas + previstas')+stat('Despesas do mês',brl(d.expense),'Pagas + pendentes')+stat('Saldo visível nas contas',brl(accounts.reduce((s,a)=>s+Number(a.visible_balance),0)),'Somente movimentações liquidadas',true)+stat('Economia realizada',brl(d.savings),'Recebidas menos pagas')+stat('Contas a pagar',brl(d.pending),'Pendências do mês')+stat('Saldo líquido previsto',brl(d.forecast),'Receitas menos despesas do mês')+stat('Despesas compartilhadas',brl(d.shared),'Contadas uma única vez')+stat('Renda comprometida',d.committed_percent===null?'—':Number(d.committed_percent).toLocaleString('pt-BR')+'%','Despesas sobre receitas previstas');
 $('#recent').innerHTML=table(entries.slice(0,5));renderEntries();$('#visibility').textContent=d.visibility;
 $('#account-list').innerHTML=accounts.length?accounts.map(a=>stat(a.name,brl(a.visible_balance),'Saldo visível · inicial '+brl(a.initial_balance))).join(''):'<p>Cadastre sua primeira conta para começar.</p>';
 $('#settlement').innerHTML=d.settlement.map(s=>stat(members.find(m=>m.id===s.user_id)?.name,brl(s.net),Number(s.net)>0?'A receber':Number(s.net)<0?'A devolver':'Tudo equilibrado')).join('');
 $('#members').innerHTML=members.map(m=>`<div class="member-row"><span>${escapeHtml(m.name)}<br><small>${escapeHtml(m.email)}</small></span><span class="badge">${m.role==='admin'?'Administrador':'Integrante'}</span></div>`).join('');
 $('#member-form').hidden=user.role!=='admin'||members.length>=2;$('#category-form').hidden=user.role!=='admin';$('#new-account').hidden=user.role!=='admin';
 $('#category-list').innerHTML=categories.map(c=>`<div class="category-row"><span>${escapeHtml(c.name)} <small>· ${c.kind==='income'?'Receita':'Despesa'}</small></span>${user.role==='admin'?`<button data-rename="${c.id}">Editar</button><button data-remove-category="${c.id}">Excluir</button>`:''}</div>`).join('');
 drawCharts();
}
function renderEntries(){const search=$('#search').value.toLocaleLowerCase();$('#entry-table').innerHTML=table(entries.filter(e=>e.kind===(page==='income'?'income':'expense')&&e.description.toLocaleLowerCase().includes(search)),true);}
function drawCharts() {
  if (!window.Chart) return;
  charts.forEach(c => c.destroy());
  charts = [];
  Chart.defaults.color = getComputedStyle(document.body).getPropertyValue('--muted');
  Chart.defaults.font.family = 'system-ui';
  charts.push(new Chart($('#flow-chart'), {
    type: 'bar',
    data: { labels: ['Receitas', 'Despesas'], datasets: [{
      data: [Number(dashboard.income), Number(dashboard.expense)],
      backgroundColor: ['#4a8969', '#d6b88b'], borderRadius: 7, barThickness: 65
    }] },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: {display: false}, tooltip: {callbacks: {label: c => brl(c.raw)}} },
      scales: {y: {beginAtZero: true, ticks: {callback: v => brl(v)}}, x: {grid: {display: false}}}
    }
  }));
  const data = Object.entries(dashboard.by_category);
  $('#empty-chart').hidden = !!data.length;
  $('#category-chart').hidden = !data.length;
  if (data.length) charts.push(new Chart($('#category-chart'), {
    type: 'doughnut',
    data: {labels: data.map(x => x[0]), datasets: [{
      data: data.map(x => Number(x[1])),
      backgroundColor: ['#3d795c','#9bac83','#d7bd92','#98b9ac','#b89888','#d1d9c8'], borderWidth: 0
    }]},
    options: {
      maintainAspectRatio: false, cutout: '72%',
      plugins: {
        legend: {position: 'right', labels: {boxWidth: 10, padding: 15}},
        tooltip: {callbacks: {label: c => c.label + ': ' + brl(c.raw)}}
      }
    }
  }));
}
const titles={dashboard:['Sua vida financeira, em sintonia.','Cada escolha de hoje aproxima vocês do amanhã.'],income:['Receitas','Tudo o que entra, organizado em um só lugar.'],expense:['Despesas','Clareza para escolher onde gastar.'],accounts:['Contas bancárias','O ponto de partida para acompanhar seus saldos.'],split:['Divisão do casal','Responsabilidades compartilhadas, sem complicação.'],settings:['Configurações','Um espaço com a cara de vocês.']};
function navigate(next){page=next;document.querySelectorAll('nav [data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===page));['dashboard','entries','accounts','split','settings'].forEach(p=>$('#'+p+'-page').hidden=p!==(page==='income'||page==='expense'?'entries':page));$('#page-title').textContent=titles[page][0];$('#page-subtitle').textContent=titles[page][1];$('#filters').hidden=['accounts','settings'].includes(page);$('#new-entry').hidden=['accounts','settings'].includes(page);$('#sidebar').classList.remove('open');renderEntries();charts.forEach(c=>c.resize());}
function entryCategories(){const f=$('#entry-form');const selected=f.elements.category_id.value;f.elements.category_id.innerHTML=options(categories.filter(c=>c.kind===f.elements.kind.value),selected);if(f.elements.kind.value==='income'){f.elements.shared.checked=false;}f.elements.shared.disabled=f.elements.kind.value==='income';}
function openEntry(id){if(!accounts.length){notify('Cadastre uma conta em Contas bancárias antes de lançar.');navigate('accounts');return;}editing=id||null;const f=$('#entry-form');f.reset();f.elements.owner_id.innerHTML=options(user.role==='admin'?members:members.filter(m=>m.id===user.id),user.id);f.elements.payer_id.innerHTML=options(members,user.id);f.elements.account_id.innerHTML=options(accounts);f.elements.kind.value=page==='income'?'income':'expense';f.elements.due_date.value=localDate();const e=entries.find(e=>e.id===id);if(e){f.elements.kind.value=e.kind;entryCategories();Object.entries(e).forEach(([k,v])=>{if(f.elements[k]){if(f.elements[k].type==='checkbox')f.elements[k].checked=v;else f.elements[k].value=v??'';}});}else entryCategories();$('#entry-title').textContent=id?'Editar lançamento':'Novo lançamento';$('#entry-dialog').showModal();}
async function submit(form,operation){const button=form.querySelector('[type="submit"],button.primary');button.disabled=true;try{await operation();}catch(e){notify(e.message);}finally{button.disabled=false;}}
$('#toggle-auth').onclick=()=>{register=!register;$('#register-fields').hidden=!register;['name','family_name'].forEach(n=>$('#auth-form').elements[n].required=register);$('#auth-submit').textContent=register?'Criar meu grupo →':'Entrar na minha conta →';$('#toggle-auth').textContent=register?'Já tenho uma conta':'Primeiro acesso? Criar meu grupo';};
$('#auth-form').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{const data=Object.fromEntries(new FormData(e.target));if(!register){delete data.name;delete data.family_name;}const result=await send('/auth/'+(register?'register':'login'),'POST',data);accessToken=result.access_token;user=await api('/me');$('#family-label').textContent=user.family_name;$('#user-name').textContent=user.name;$('#avatar').textContent=user.name.slice(0,1).toUpperCase();$('#auth').hidden=true;$('#app').hidden=false;e.target.reset();await refresh();navigate('dashboard');});};
$('#entry-form').elements.kind.onchange=entryCategories;
$('#entry-form').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{const f=e.target;const data=Object.fromEntries(new FormData(f));['owner_id','payer_id','account_id','category_id'].forEach(k=>data[k]=Number(data[k]));data.shared=f.elements.shared.checked;data.private=f.elements.private.checked;data.settled_date=data.settled_date||null;await send('/entries'+(editing?'/'+editing:''),editing?'PUT':'POST',data);$('#entry-dialog').close();await refresh();notify('Lançamento salvo.');});};
$('#account-form').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{await send('/accounts','POST',Object.fromEntries(new FormData(e.target)));e.target.reset();$('#account-dialog').close();await refresh();notify('Conta criada.');});};
$('#member-form').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{await send('/members','POST',Object.fromEntries(new FormData(e.target)));e.target.reset();await refresh();notify('Integrante adicionado.');});};
$('#category-form').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{await send('/categories','POST',Object.fromEntries(new FormData(e.target)));e.target.reset();await refresh();notify('Categoria criada.');});};
document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;try{if(b.dataset.page)navigate(b.dataset.page);if(b.dataset.close)$('#'+b.dataset.close).close();if(b.dataset.edit)openEntry(Number(b.dataset.edit));if(b.dataset.delete&&confirm('Cancelar este lançamento? O histórico será preservado na auditoria.')){await api('/entries/'+b.dataset.delete,{method:'DELETE'});await refresh();notify('Lançamento cancelado.');}if(b.dataset.removeCategory&&confirm('Excluir categoria sem histórico?')){await api('/categories/'+b.dataset.removeCategory,{method:'DELETE'});await refresh();}if(b.dataset.rename){const c=categories.find(c=>c.id===Number(b.dataset.rename));const name=prompt('Novo nome da categoria',c.name);if(name){await send('/categories/'+c.id,'PUT',{name,kind:c.kind});await refresh();}}}catch(error){notify(error.message);}});
$('#new-entry').onclick=()=>openEntry();$('#new-account').onclick=()=>$('#account-dialog').showModal();$('#logout').onclick=logout;$('#menu').onclick=()=>$('#sidebar').classList.toggle('open');$('#search').oninput=renderEntries;
$('#month').value=localDate().slice(0,7);['#month','#filter-owner','#filter-category','#filter-account'].forEach(s=>$(s).onchange=()=>{if($('#month').value)refresh().catch(e=>notify(e.message));});
if(localStorage.getItem('finance-theme')==='dark')document.body.classList.add('dark');$('#theme').onclick=()=>{document.body.classList.toggle('dark');localStorage.setItem('finance-theme',document.body.classList.contains('dark')?'dark':'light');drawCharts();};
