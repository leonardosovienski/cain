// Question map of the adversarial review (read-only view of GET /review/{domain}/{hypothesis}).
const form = document.getElementById('pick');
const params = new URLSearchParams(location.search);
form.domain.value = params.get('domain') || '';
form.hypothesis.value = params.get('hypothesis') || '';

function cell(text) {
  const td = document.createElement('td');
  td.textContent = text;
  return td;
}

async function load(domain, hypothesis) {
  const response = await fetch(`/review/${encodeURIComponent(domain)}/${encodeURIComponent(hypothesis)}`);
  const summary = document.getElementById('summary');
  const rows = document.getElementById('rows');
  rows.replaceChildren();
  if (!response.ok) {
    summary.textContent = `Não encontrado (${response.status}).`;
    return;
  }
  const map = await response.json();
  summary.textContent = `${map.hypothesis_id} (${map.state}): ${map.blocking.length} item(ns) obrigatório(s) bloqueando; ` +
    (map.ready_to_preregister ? 'pronto para pré-registro.' : 'pré-registro recusado até resolver.');
  for (const q of map.questions) {
    const row = document.createElement('tr');
    if (map.blocking.includes(q.item_id)) row.className = 'blocking';
    const detail = q.waiver ? `dispensa: ${q.waiver.by} — ${q.waiver.reason}`
      : q.answered_by ? `respondida: ${q.answered_by.ref}`
      : q.test ? `${q.test.kind}: ${q.test.description} (critério: ${q.test.pass_criterion})`
      : q.not_testable_reason ? `não testável: ${q.not_testable_reason}`
      : q.matches && q.matches.length ? `equivalente a: ${q.matches.map(m => `${m.finding_id} (${m.verdict})`).join(', ')}`
      : '';
    row.append(cell(q.perspective_name + (q.mandatory ? ' *' : '')), cell(q.question), cell(q.status), cell(detail));
    rows.append(row);
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  history.replaceState(null, '', `?domain=${encodeURIComponent(form.domain.value)}&hypothesis=${encodeURIComponent(form.hypothesis.value)}`);
  load(form.domain.value, form.hypothesis.value);
});
if (form.domain.value && form.hypothesis.value) load(form.domain.value, form.hypothesis.value);
