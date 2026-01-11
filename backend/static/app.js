(function(){
  const el = {
    search: null, state: null, segment: null, table: null
  };

  function chip(label, kind){
    const cls = kind === 'ok' ? 'chip ok' : kind === 'warn' ? 'chip warn' : kind === 'bad' ? 'chip bad' : 'chip';
    return `<span class="${cls}" aria-label="${label}">${label}</span>`;
  }

  function stateChip(state){
    const map = {
      REFERRAL_RECEIVED: 'info', INTAKE_COMPLETE: 'ok', ASSESSMENT_COMPLETE: 'ok',
      ELIGIBILITY_VERIFIED: 'ok', AUTH_PENDING: 'warn', AUTH_APPROVED: 'ok', READY_TO_SCHEDULE: 'ok'
    };
    const kind = map[state] || 'info';
    return chip(state, kind === 'ok' ? 'ok' : kind === 'warn' ? 'warn' : '');
  }

  function boolChip(val, trueLabel, falseLabel){
    const v = String(val).toLowerCase();
    if(v === 'true' || v === 'yes' || v === '1') return chip(trueLabel || 'Yes','ok');
    if(v === 'false' || v === 'no' || v === '0') return chip(falseLabel || 'No','bad');
    return chip('—','');
  }

  function renderTable(rows){
    const header = [
      'Referral', 'State', 'Segment', 'City', 'Payer', 'Plan',
      'Ready To Schedule', 'Eligibility Verified', 'Auth Required', 'Auth Approved', 'Caregiver'
    ];
    const thead = '<thead><tr>' + header.map(h=>`<th>${h}</th>`).join('') + '</tr></thead>';
    const tbody = '<tbody>' + rows.map(r=>{
      return `<tr>
        <td>${r.referral_id}</td>
        <td>${stateChip(r.state)}</td>
        <td>${r.agent_segment ? chip(r.agent_segment,'') : '—'}</td>
        <td>${r.patient_city || '—'}</td>
        <td>${r.payer || '—'}</td>
        <td>${r.plan_type || '—'}</td>
        <td>${boolChip(r.ready_to_schedule,'Ready','Not Ready')}</td>
        <td>${boolChip(r.eligibility_verified,'Verified','Not Verified')}</td>
        <td>${boolChip(r.auth_required,'Required','Not Required')}</td>
        <td>${boolChip(r.auth_approved,'Approved','Not Approved')}</td>
        <td>${r.matched_caregiver_id || '—'}</td>
      </tr>`;
    }).join('') + '</tbody>';
    el.table.innerHTML = `<div class='table-container'><table class='data-table'>${thead}${tbody}</table></div>`;
  }

  function applyFilters(all){
    const q = (el.search.value || '').trim().toLowerCase();
    const st = el.state.value || '';
    const seg = el.segment.value || '';
    return all.filter(r=>{
      const matchesQ = !q || (String(r.referral_id).toLowerCase().includes(q) || String(r.patient_city||'').toLowerCase().includes(q));
      const matchesSt = !st || r.state === st;
      const matchesSeg = !seg || (String(r.agent_segment||'') === seg);
      return matchesQ && matchesSt && matchesSeg;
    });
  }

  async function init(){
    el.search = document.getElementById('search');
    el.state = document.getElementById('state');
    el.segment = document.getElementById('segment');
    el.table = document.getElementById('table');

    const res = await fetch('/api/outcomes');
    const json = await res.json();
    const all = json.data || [];

    function update(){ renderTable(applyFilters(all)); }
    el.search.addEventListener('input', update);
    el.state.addEventListener('change', update);
    el.segment.addEventListener('change', update);

    update();
  }

  window.addEventListener('DOMContentLoaded', init);
})();
