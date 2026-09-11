const $ = (id) => document.getElementById(id);
const state = { user: 'leo', project: null, session: null, busy: false, profile: null, memoryTurn: null };
const names = { format: 'Formato', verbosity: 'Extensão', language: 'Idioma' };
const values = { bullets: 'Tópicos', paragraph: 'Parágrafo', steps: 'Passos', short: 'Curta', detailed: 'Detalhada', pt: 'Português', en: 'Inglês' };
const scopes = { user: 'Padrão geral', project: 'Neste projeto', session: 'Nesta conversa', turn: 'Só nesta resposta' };
const reasons = { incorrect: 'Informação incorreta', format: 'Formato inadequado', source: 'Problema com a fonte', memory: 'Preferência não respeitada', long: 'Resposta longa demais' };
const empty = $('empty').cloneNode(true);
const pathUser = () => encodeURIComponent(state.user);
const context = (extra = {}) => ({ project_id: state.project, session_id: state.session, ...extra });
function query(data) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(data)) if (value !== null && value !== undefined && value !== '') params.set(key, value);
  const result = params.toString();
  return result ? '?' + result : '';
}
function node(tag, text, className) {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (className) result.className = className;
  return result;
}
function notice(message = '') {
  $('notice').textContent = message;
  $('notice').hidden = !message;
}
async function api(path, method = 'GET', body) {
  const response = await fetch(path, {
    method, headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Verifique os campos e tente novamente.';
    throw new Error(detail);
  }
  return data;
}
function updateControls() {
  for (const element of document.querySelectorAll('button,select,input,textarea:not(#message)')) element.disabled = state.busy;
  $('send').disabled = state.busy || !state.session;
  $('add-document').disabled = state.busy || !state.project;
  for (const id of ['edit-scope', 'preference-scope']) {
    $(id).querySelector('option[value="project"]').disabled = !state.project;
    if (!state.project && $(id).value === 'project') $(id).value = id === 'edit-scope' ? 'user' : '';
  }
  $('activity').textContent = state.busy ? 'Processando no computador…' : 'Enter envia · Shift + Enter quebra a linha';
}
async function action(work) {
  if (state.busy) throw new Error('Aguarde o pedido atual terminar.');
  state.busy = true;
  updateControls();
  notice();
  try { return await work(); }
  finally { state.busy = false; updateControls(); }
}
const handle = (work) => () => action(work).catch((error) => notice(error.message));
function selectOptions(select, entries, placeholder) {
  select.replaceChildren();
  if (placeholder) select.append(new Option(placeholder, ''));
  for (const entry of entries) select.append(new Option(entry.name ?? entry.title, entry.id));
}
async function loadProjects(preferred = null) {
  const projects = await api(`/projects/${pathUser()}`);
  selectOptions($('project'), projects, 'Geral');
  state.project = projects.some((p) => p.id === preferred) ? preferred : null;
  $('project').value = state.project ?? '';
  await loadProject();
}
async function loadProject() {
  $('research-result').replaceChildren();
  state.session = null;
  $('project-title').textContent = $('project').selectedOptions[0].textContent;
  const sessions = await api(`/sessions/${pathUser()}` + query({ project_id: state.project }));
  selectOptions($('session'), sessions);
  if (!sessions.length) {
    const session = await api(`/sessions/${pathUser()}`, 'POST', { project_id: state.project });
    $('session').append(new Option(session.title, session.id));
    state.session = session.id;
  } else state.session = sessions[0].id;
  $('session').value = state.session;
  await loadConversation();
  await loadDocuments();
}
async function loadDocuments() {
  $('document-list').replaceChildren();
  if (!state.project) {
    $('document-hint').textContent = 'Geral usa as fontes locais da configuração. Crie um projeto para adicionar arquivos.';
    return;
  }
  const documents = await api(`/projects/${pathUser()}/${encodeURIComponent(state.project)}/documents`);
  $('document-hint').textContent = documents.length ? `${documents.length} documento(s) neste projeto.` : 'Adicione um texto para consultar nas conversas deste projeto.';
  for (const document of documents) {
    const item = node('li', document.title);
    item.append(node('small', 'Versão ' + document.content_hash.slice(0, 10)));
    $('document-list').append(item);
  }
}
async function loadConversation() {
  const turns = await api(`/sessions/${pathUser()}/${encodeURIComponent(state.session)}` + query({ project_id: state.project }));
  $('messages').replaceChildren();
  if (!turns.length) $('messages').append(empty.cloneNode(true));
  for (const turn of turns) {
    addMessage('user', turn.payload);
    addResponse({ ...turn.result, turn_id: turn.id });
  }
  await refreshProfile();
  scrollMessages();
}
function scrollMessages() { $('messages').scrollTop = $('messages').scrollHeight; }
function renderText(container, text) {
  // Model output and source material remain text. Only fenced blocks get formatting.
  const pattern = /```[^\n]*\n([\s\S]*?)```/g;
  let position = 0;
  for (const match of text.matchAll(pattern)) {
    container.append(document.createTextNode(text.slice(position, match.index)));
    const pre = node('pre');
    pre.append(node('code', match[1].replace(/\n$/, '')));
    container.append(pre);
    position = match.index + match[0].length;
  }
  container.append(document.createTextNode(text.slice(position)));
}
function addMessage(role, text, extraClass = '') {
  $('messages').querySelector('.empty')?.remove();
  const article = node('article', undefined, `message ${role} ${extraClass}`);
  article.append(node('div', role === 'user' ? 'VOCÊ' : 'CAIN', 'message-label'));
  const content = node('div', undefined, 'message-content');
  renderText(content, text);
  article.append(content);
  $('messages').append(article);
  return article;
}
function sourceDetails(source) {
  const details = node('details', undefined, 'source-details');
  details.append(node('summary', `${source.citation ?? ''} ${source.title || 'Trecho consultado'}`.trim()));
  details.append(node('pre', source.excerpt ?? source.text ?? 'Trecho indisponível.'));
  if (source.excerpt_truncated) details.append(node('p', 'Trecho abreviado para caber no contexto enviado.', 'muted'));
  details.append(node('small', 'Origem: ' + (source.source ?? 'Documento local')));
  if (source.document_hash) details.append(node('small', 'SHA-256 do documento: ' + source.document_hash));
  if (source.excerpt_hash) details.append(node('small', 'SHA-256 do trecho: ' + source.excerpt_hash));
  if (source.start_offset !== null && source.start_offset !== undefined) {
    details.append(node('small', `Posição no texto: ${source.start_offset}–${source.end_offset} (fim exclusivo).`));
  }
  return details;
}
function addResponse(result) {
  const article = addMessage('assistant', result.response);
  for (const source of result.sources ?? []) article.append(sourceDetails(source));
  const tools = node('div', undefined, 'feedback');
  const used = Object.entries(result.preferences_used ?? {}).map(([key, value]) => `${names[key] ?? key}: ${values[value] ?? value}`);
  if (used.length) article.append(node('p', used.join(' · '), 'footnote'));
  const inspect = node('button', 'Memória desta resposta');
  inspect.type = 'button';
  inspect.addEventListener('click', handle(async () => {
    await refreshProfile(result.decision_id);
    document.querySelector('.shell').classList.remove('memory-hidden');
    $('toggle-memory').setAttribute('aria-expanded', 'true');
  }));
  tools.append(inspect);
  const useful = node('button', 'Foi útil');
  useful.type = 'button';
  const feedbackStatus = node('span');
  feedbackStatus.setAttribute('role', 'status');
  useful.addEventListener('click', handle(async () => {
    await api(`/feedback/${encodeURIComponent(result.turn_id)}`, 'POST', { user_id: state.user, reason: 'useful' });
    feedbackStatus.textContent = 'Avaliação registrada.';
  }));
  tools.append(useful, feedbackStatus);
  article.append(tools);
  const details = node('details', undefined, 'feedback-details');
  details.append(node('summary', 'Sinalizar um problema'));
  const form = node('form');
  const label = node('label', 'O que precisa melhorar?');
  const select = node('select');
  for (const [value, text] of Object.entries(reasons)) select.append(new Option(text, value));
  label.append(select);
  const noteLabel = node('label', 'Comentário (opcional)');
  const note = node('textarea');
  note.maxLength = 2000;
  note.rows = 2;
  noteLabel.append(note);
  const submit = node('button', 'Registrar avaliação', 'secondary');
  submit.type = 'submit';
  form.append(label, noteLabel, submit);
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    handle(async () => {
      await api(`/feedback/${encodeURIComponent(result.turn_id)}`, 'POST', { user_id: state.user, reason: select.value, note: note.value });
      feedbackStatus.textContent = 'Problema registrado para revisão. O perfil não foi alterado.';
      details.open = false;
      note.value = '';
    })();
  });
  details.append(form);
  article.append(details);
  return article;
}
async function refreshProfile(turnId = null) {
  const profile = await api(`/profile/${pathUser()}` + query(context({ turn_id: turnId })));
  state.memoryTurn = turnId;
  state.profile = profile;
  renderProfile(profile);
  return profile;
}
function renderProfile(profile) {
  $('memory-context').textContent = state.memoryTurn
    ? 'Valores atuais nos escopos desta resposta. A lista abaixo da mensagem registra o que foi usado ao responder.'
    : 'O que vale para a próxima resposta e de onde veio.';
  $('effective-profile').replaceChildren();
  for (const [key, name] of Object.entries(names)) {
    const card = node('div', undefined, 'preference-card');
    card.append(node('div', name, 'field'));
    const value = profile.effective_preferences[key];
    card.append(node('strong', value ? values[value] ?? value : 'Sem preferência definida'));
    if (value) card.append(node('small', scopes[profile.effective_provenance[key]?.scope] ?? 'Padrão geral'));
    $('effective-profile').append(card);
  }
  $('memory-history').replaceChildren();
  let count = 0;
  for (const scope of ['turn', 'session', 'project', 'user']) {
    for (const [key, entry] of Object.entries(profile.scoped_preferences[scope] ?? {})) {
      count++;
      const details = node('details', undefined, 'memory-entry');
      const status = { active: 'Ativa', removed: 'Removida', expired: 'Expirada' }[entry.status] ?? entry.status;
      details.append(node('summary', `${names[key] ?? key} · ${scopes[scope]} · ${status}`));
      if (entry.value) details.append(node('p', 'Valor: ' + (values[entry.value] ?? entry.value)));
      const provenance = entry.provenance ?? {};
      if (provenance.evidence) details.append(node('p', 'Origem: ' + provenance.evidence));
      if (provenance.observed_at) details.append(node('p', 'Registrada em ' + new Date(provenance.observed_at).toLocaleString('pt-BR')));
      if (entry.expires_at) details.append(node('p', 'Validade: ' + new Date(entry.expires_at).toLocaleString('pt-BR')));
      if (entry.status === 'active') {
        const remove = node('button', 'Remover deste escopo');
        remove.type = 'button';
        remove.addEventListener('click', handle(async () => {
          await api(`/profile/${pathUser()}/preferences/${key}` + query(context({ scope, turn_id: scope === 'turn' ? state.memoryTurn : null })), 'DELETE');
          await refreshProfile(state.memoryTurn);
        }));
        details.append(remove);
      }
      $('memory-history').append(details);
    }
  }
  if (!count) $('memory-history').append(node('p', 'As preferências que você declarar aparecerão aqui.', 'muted'));
}
async function sendRequest(text, preferenceScope = null) {
  if (!state.session) throw new Error('Abra uma conversa primeiro.');
  if (typeof text !== 'string' || !text.trim() || text.length > 100000) throw new Error('Escreva uma mensagem de até 100.000 caracteres.');
  addMessage('user', text);
  const pending = addMessage('assistant', 'Preparando a resposta…');
  scrollMessages();
  let result;
  try {
    result = await api('/run', 'POST', { user_id: state.user, ...context(), payload: text, preference_scope: preferenceScope });
  } catch (error) {
    // No automatic resend: generation may have produced an audited failure.
    pending.remove();
    addMessage('assistant', 'O pedido falhou: ' + error.message, 'error');
    try { await refreshProfile(); } catch { /* The refresh button remains available. */ }
    scrollMessages();
    throw error;
  }
  pending.remove();
  addResponse(result);
  if ($('message').value === text) $('message').value = '';
  try {
    await refreshProfile();
    const sessions = await api(`/sessions/${pathUser()}` + query({ project_id: state.project }));
    selectOptions($('session'), sessions);
    $('session').value = state.session;
  } catch (error) {
    notice('Resposta salva. Não foi possível atualizar o painel: ' + error.message);
  }
  scrollMessages();
  return result;
}
$('composer').addEventListener('submit', (event) => {
  event.preventDefault();
  handle(() => sendRequest($('message').value, $('preference-scope').value || null))();
});
$('message').addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    if (!state.busy && state.session) $('composer').requestSubmit();
  }
});
$('messages').addEventListener('click', (event) => {
  const button = event.target.closest('[data-example]');
  if (button) { $('message').value = button.dataset.example; $('message').focus(); }
});
$('project').addEventListener('change', handle(async () => { state.project = $('project').value || null; await loadProject(); }));
$('session').addEventListener('change', handle(async () => { state.session = $('session').value; await loadConversation(); }));
$('new-session').addEventListener('click', handle(async () => {
  const session = await api(`/sessions/${pathUser()}`, 'POST', { project_id: state.project });
  $('session').prepend(new Option(session.title, session.id));
  state.session = session.id;
  $('session').value = session.id;
  await loadConversation();
}));
$('change-user').addEventListener('click', handle(async () => {
  const user = $('user').value.trim();
  if (!user) throw new Error('Preencha o nome do usuário.');
  state.user = user;
  try { localStorage.setItem('cain.user', user); } catch { /* Storage is optional. */ }
  await loadProjects();
}));
$('refresh-profile').addEventListener('click', handle(() => refreshProfile()));
$('toggle-memory').addEventListener('click', () => {
  const hidden = document.querySelector('.shell').classList.toggle('memory-hidden');
  $('toggle-memory').setAttribute('aria-expanded', String(!hidden));
});
$('close-memory').addEventListener('click', () => {
  document.querySelector('.shell').classList.add('memory-hidden');
  $('toggle-memory').setAttribute('aria-expanded', 'false');
  $('toggle-memory').focus();
});
function preferenceValues() {
  const allowed = { format: ['bullets', 'paragraph', 'steps'], verbosity: ['short', 'detailed'], language: ['pt', 'en'] };
  $('preference-value').replaceChildren(...allowed[$('preference-key').value].map((value) => new Option(values[value], value)));
}
$('preference-key').addEventListener('change', preferenceValues);
$('preference-form').addEventListener('submit', (event) => {
  event.preventDefault();
  handle(async () => {
    const expiresAt = $('expires').value ? new Date($('expires').value).toISOString() : null;
    await api(`/profile/${pathUser()}/preferences/${$('preference-key').value}`, 'PUT', {
      ...context(), value: $('preference-value').value, scope: $('edit-scope').value, expires_at: expiresAt,
    });
    await refreshProfile();
    notice('Preferência salva. Ela será aplicada aos próximos pedidos deste contexto.');
  })();
});
$('new-project').addEventListener('click', () => $('project-dialog').showModal());
$('add-document').addEventListener('click', () => $('document-dialog').showModal());
for (const button of document.querySelectorAll('[data-close]')) button.addEventListener('click', () => $(button.dataset.close).close());
$('project-form').addEventListener('submit', (event) => {
  event.preventDefault();
  handle(async () => {
    const project = await api(`/projects/${pathUser()}`, 'POST', { name: $('project-name').value });
    $('project-dialog').close();
    $('project-form').reset();
    await loadProjects(project.id);
  })();
});
$('document-file').addEventListener('change', handle(async () => {
  const file = $('document-file').files[0];
  if (!file) return;
  if (file.size > 262144) throw new Error('Escolha um arquivo de até 256 KiB.');
  if (!/\.(txt|md|rst)$/i.test(file.name)) throw new Error('Use .txt, .md ou .rst.');
  $('document-name').value = file.name;
  $('document-text').value = await file.text();
}));
$('document-form').addEventListener('submit', (event) => {
  event.preventDefault();
  handle(async () => {
    await api(`/projects/${pathUser()}/${encodeURIComponent(state.project)}/documents`, 'POST', {
      title: $('document-name').value, content: $('document-text').value,
    });
    $('document-dialog').close();
    $('document-form').reset();
    await loadDocuments();
    notice('Documento salvo. Você já pode pedir uma busca sobre ele.');
  })();
});

// Optional WebMCP surface: the exact same actions and context as the visible UI.
if (typeof navigator.modelContext?.registerTool === 'function') {
  navigator.modelContext.registerTool({
    name: 'cain_get_profile', description: 'Lê as preferências efetivas do usuário e conversa selecionados no Cain.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true },
    execute: async () => ({ content: [{ type: 'text', text: JSON.stringify(await action(() => refreshProfile())) }] }),
  });
  navigator.modelContext.registerTool({
    name: 'cain_send_request', description: 'Envia um pedido na conversa selecionada. Preferências explícitas na frase podem atualizar o perfil local.',
    inputSchema: { type: 'object', properties: { text: { type: 'string', minLength: 1, maxLength: 100000 } }, required: ['text'], additionalProperties: false },
    execute: async ({ text }) => ({ content: [{ type: 'text', text: JSON.stringify(await action(() => sendRequest(text, $('preference-scope').value || null))) }] }),
  });
}

function researchBody(offset = 0) {
  return { user_id: state.user, project_id: state.project,
    collection: $('research-collection').value,
    source_id: $('research-id').value || null, status: $('research-status').value || null,
    text: $('research-text').value || null, limit: 10, offset };
}
function renderResearch(result) {
  const container = $('research-result');
  container.replaceChildren();
  const facts = result.facts ?? result;
  container.append(node('p', `${facts.total_record_revisions} revisões de registros no escopo admitido. Não é contagem de experimentos.`));
  const coverage = node('details');
  coverage.append(node('summary', 'Cobertura, lacunas e limitações'));
  coverage.append(node('pre', JSON.stringify({ coverage: facts.coverage, limitations: facts.limitations, conflicts: facts.conflicts, multiple_revisions: facts.multiple_revisions }, null, 2)));
  container.append(coverage);
  for (const record of facts.records) {
    const article = node('article', undefined, 'research-record');
    article.append(node('h3', `${record.source_id} · ${record.source_status}`));
    article.append(node('p', `Eixo: ${record.status_axis} · Tipo: ${record.kind} · Mapeamento: ${record.mapping ? JSON.stringify(record.mapping) : 'não atribuído'}`));
    article.append(node('small', `Revisão: ${record.revision} · Identidade: ${record.identity_basis}`));
    article.append(node('p', record.reason ?? 'Motivo estruturado não registrado; consulte o relato da fonte.'));
    for (const evidence of record.evidence) {
      const detail = node('details');
      detail.append(node('summary', `${evidence.source} · ${evidence.availability}`));
      detail.append(node('pre', evidence.text ?? 'Somente referência; conteúdo não recebido.'));
      detail.append(node('small', `${evidence.locator} · ${evidence.start}–${evidence.end} ${evidence.offset_unit ?? ''}`));
      detail.append(node('small', `SHA-256 (${evidence.hash_basis ?? 'indisponível'}): ${evidence.sha256 ?? 'indisponível'}`));
      const inspect = node('button', 'Inspecionar evidência preservada', 'secondary');
      inspect.type = 'button';
      inspect.addEventListener('click', handle(async () => {
        const preserved = await api('/research/evidence/' + encodeURIComponent(evidence.reference_id) + query({ user_id: state.user, project_id: state.project, collection: $('research-collection').value }));
        const pre = node('pre', JSON.stringify(preserved, null, 2));
        inspect.replaceWith(pre);
      }));
      detail.append(inspect);
      article.append(detail);
    }
    container.append(article);
  }
  if (facts.offset > 0) {
    const previous = node('button', 'Página anterior', 'secondary');
    previous.addEventListener('click', handle(() => runResearch(Math.max(0, facts.offset - facts.limit))));
    container.append(previous);
  }
  if (facts.has_more) {
    const next = node('button', 'Próxima página', 'secondary');
    next.addEventListener('click', handle(() => runResearch(facts.offset + facts.limit)));
    container.append(next);
  }
  if (result.generation) {
    const explanation = node('details');
    explanation.open = true;
    explanation.append(node('summary', `Explicação opcional: ${result.status} · síntese proposta, suporte semântico não certificado`));
    explanation.append(node('pre', JSON.stringify({ explanation: result.explanation, generation: result.generation, error: result.error }, null, 2)));
    container.append(explanation);
  }
}
async function runResearch(offset = 0) {
  renderResearch(await api('/research/query', 'POST', researchBody(offset)));
}
$('research-form').addEventListener('submit', (event) => {
  event.preventDefault();
  handle(() => runResearch())();
});
$('research-explain').addEventListener('click', handle(async () => {
  renderResearch(await api('/research/explain', 'POST', { ...researchBody(), question: $('research-question').value }));
}));

preferenceValues();
if (matchMedia('(max-width:1150px)').matches) {
  document.querySelector('.shell').classList.add('memory-hidden');
  $('toggle-memory').setAttribute('aria-expanded', 'false');
}
try { state.user = localStorage.getItem('cain.user') || state.user; } catch { /* Storage is optional. */ }
$('user').value = state.user;
handle(async () => {
  const health = await api('/health');
  $('model').textContent = 'Modelo configurado: ' + health.model;
  $('search-mode').textContent = health.search_mode === 'hybrid' ? 'Busca híbrida configurada · disponibilidade não verificada' : 'Busca por palavras · serviço local';
  await loadProjects();
})();
