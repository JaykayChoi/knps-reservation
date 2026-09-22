import { api, jsonOptions } from './api.js';
import { createStationPicker } from './stations.js';

const PARKS = ['가야산','계룡산','내장산','내장산백암','다도해해상','덕유산','무등산동부','변산반도','북한산','설악산','소백산','소백산북부','오대산','월악산','월출산','주왕산','지리산경남','지리산전북','치악산','태백산','태안해안','팔공산동부','팔공산서부','한려해상','한려해상동부'];
const labels = { knps: 'KNPS', moduparking: 'Parking', ktx: 'KTX' };
const byId = id => document.getElementById(id);
const checked = name => Array.from(document.querySelectorAll(`input[name="${name}"]:checked`), input => input.value);
let monitors = [];

function toast(message, type = 'success') {
  const element = document.createElement('div');
  element.className = `toast-enter px-4 py-3 border-2 border-forest-950 shadow-brutal ${type === 'success' ? 'bg-forest-950' : 'bg-alert'} text-white`;
  element.textContent = message; byId('toast-container').appendChild(element);
  setTimeout(() => element.remove(), 3000);
}

function checkbox(container, name, value, label) {
  const wrapper = document.createElement('label'); wrapper.className = 'flex items-center gap-2 py-1';
  const input = document.createElement('input'); input.type = 'checkbox'; input.name = name;
  input.value = value; input.className = 'brutal-checkbox';
  const text = document.createElement('span'); text.textContent = label; wrapper.append(input, text); container.appendChild(wrapper);
}

async function loadCatalogs() {
  const parks = byId('parks-container'); PARKS.forEach(park => checkbox(parks, 'selected_parks', park, park));
  try {
    const lots = await api('/api/parking-lots');
    lots.forEach(lot => checkbox(byId('parkinglots-container'), 'parking_lot_ids', lot.seq, lot.name));
  } catch { byId('parkinglots-container').textContent = 'Failed to load parking lots'; }
}

function setCategory(category) {
  if (!labels[category]) return;
  byId('category').value = category;
  document.querySelectorAll('[data-category]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.category === category)));
  document.querySelectorAll('[data-for-category]').forEach(section => {
    section.hidden = section.dataset.forCategory !== category;
    section.querySelectorAll('input,button').forEach(input => { input.disabled = section.hidden; });
  });
  byId('category-dropzone').textContent = `Selected: ${labels[category]}`;
}

function setDateMode(mode) {
  byId('weekday-section').classList.toggle('hidden', mode !== 'weekday');
  byId('absolute-section').classList.toggle('hidden', mode !== 'absolute');
}

function setQuietEnabled(enabled) {
  byId('quiet_hours_enabled').checked = enabled;
  byId('quiet-hours-fields').classList.toggle('opacity-50', !enabled);
  byId('quiet_hours_start').disabled = !enabled;
  byId('quiet_hours_end').disabled = !enabled;
}

function resetForm() {
  byId('settings-form').reset(); byId('monitor_id').value = ''; setCategory('knps'); setDateMode('weekday');
  byId('telegram_bot_token').placeholder = ''; byId('telegram_chat_id').placeholder = '';
  byId('is_active').checked = true; byId('include_waiting').checked = true;
  document.querySelectorAll('input[name="ktx_seat_classes"]').forEach(input => { input.checked = input.value !== 'standing'; });
  setQuietEnabled(false); byId('quiet_hours_start').value = '23:00'; byId('quiet_hours_end').value = '07:00';
}

function fillChecks(name, values) {
  document.querySelectorAll(`input[name="${name}"]`).forEach(input => { input.checked = (values || []).map(String).includes(input.value); });
}

function populate(monitor) {
  const options = monitor.options || {};
  setCategory(monitor.category); byId('monitor_id').value = monitor.id; byId('name').value = monitor.name;
  byId('is_active').checked = monitor.is_active !== false; byId('cooldown_days').value = monitor.cooldown_days;
  byId('telegram_bot_token').value = ''; byId('telegram_chat_id').value = '';
  const secretPlaceholder = monitor.telegram_configured ? 'Configured — leave blank to keep' : '';
  byId('telegram_bot_token').placeholder = secretPlaceholder; byId('telegram_chat_id').placeholder = secretPlaceholder;
  setQuietEnabled(Boolean(monitor.quiet_hours_enabled)); byId('quiet_hours_start').value = String(monitor.quiet_hours_start || '23:00').slice(0,5); byId('quiet_hours_end').value = String(monitor.quiet_hours_end || '07:00').slice(0,5);
  if (monitor.category === 'knps') {
    byId('include_waiting').checked = options.include_waiting !== false; byId('weeks_ahead').value = options.weeks_ahead;
    byId('start_date').value = options.start_date || ''; byId('end_date').value = options.end_date || '';
    const mode = options.date_mode || 'weekday'; document.querySelector(`input[name="date_mode"][value="${mode}"]`).checked = true; setDateMode(mode);
    fillChecks('selected_days', options.days); fillChecks('selected_types', options.facility_types); fillChecks('selected_parks', options.parks);
  } else if (monitor.category === 'moduparking') fillChecks('parking_lot_ids', options.lot_ids);
  else {
    ['departure','arrival','departure_code','arrival_code','date','start_time','end_time'].forEach(key => { byId(`ktx_${key}`).value = options[key] || ''; });
    fillChecks('ktx_seat_classes', options.seat_classes);
  }
}

function openModal(id = null) {
  resetForm(); byId('modal-title').textContent = id ? 'Edit Setting' : 'Add New Setting';
  byId('btn-clear-history').classList.toggle('hidden', !id);
  if (id) populate(monitors.find(item => item.id === id));
  byId('setting-modal').classList.remove('hidden'); document.body.style.overflow = 'hidden';
}

function closeModal() { byId('setting-modal').classList.add('hidden'); document.body.style.overflow = ''; }

function formData() {
  const category = byId('category').value;
  let options;
  if (category === 'knps') options = { date_mode: document.querySelector('input[name="date_mode"]:checked').value,
    weeks_ahead: Number(byId('weeks_ahead').value), days: checked('selected_days'), start_date: byId('start_date').value || null,
    end_date: byId('end_date').value || null, parks: checked('selected_parks'), facility_types: checked('selected_types'), include_waiting: byId('include_waiting').checked };
  else if (category === 'moduparking') options = { lot_ids: checked('parking_lot_ids') };
  else {
    options = { departure: byId('ktx_departure').value, arrival: byId('ktx_arrival').value, date: byId('ktx_date').value,
      start_time: byId('ktx_start_time').value, end_time: byId('ktx_end_time').value, seat_classes: checked('ktx_seat_classes') };
    if (byId('ktx_departure_code').value && byId('ktx_arrival_code').value) Object.assign(options, { departure_code: byId('ktx_departure_code').value, arrival_code: byId('ktx_arrival_code').value });
  }
  const payload = { name: byId('name').value, category, options, is_active: byId('is_active').checked,
    cooldown_days: Number(byId('cooldown_days').value), quiet_hours_enabled: byId('quiet_hours_enabled').checked,
    quiet_hours_start: byId('quiet_hours_start').value, quiet_hours_end: byId('quiet_hours_end').value,
    telegram_bot_token: byId('telegram_bot_token').value, telegram_chat_id: byId('telegram_chat_id').value };
  const current = monitors.find(item => String(item.id) === byId('monitor_id').value);
  if (current?.telegram_configured) {
    if (!payload.telegram_bot_token) delete payload.telegram_bot_token;
    if (!payload.telegram_chat_id) delete payload.telegram_chat_id;
  }
  return payload;
}

function details(monitor) {
  const o = monitor.options || {};
  if (monitor.category === 'ktx') return `${o.departure || ''} → ${o.arrival || ''} · ${o.date || ''} · ${(o.seat_classes || []).join(', ')}`;
  if (monitor.category === 'moduparking') return `Parking lots: ${(o.lot_ids || []).length}`;
  return o.date_mode === 'absolute' ? `${o.start_date || ''} to ${o.end_date || ''}` : `${o.weeks_ahead || 0} wks (${(o.days || []).join(',')})`;
}

function render() {
  const container = byId('settings-list'); container.replaceChildren();
  if (!monitors.length) { const empty = byId('empty-state'); empty.classList.remove('hidden'); container.appendChild(empty); return; }
  monitors.forEach(monitor => {
    const card = document.createElement('article'); card.className = 'brutal-card p-6 flex flex-col gap-4';
    const active = monitor.is_active !== false;
    const title = document.createElement('h3'); title.className = 'font-serif text-xl font-bold'; title.textContent = monitor.name;
    const badge = document.createElement('span'); badge.className = `shrink-0 border-2 border-forest-950 px-2 py-1 text-xs font-bold uppercase tracking-wide ${active ? 'bg-forest-950 text-white' : 'bg-sand text-forest-950'}`;
    badge.textContent = active ? 'Active' : 'Paused';
    const heading = document.createElement('div'); heading.className = 'flex items-start justify-between gap-3'; heading.append(title, badge);
    const info = document.createElement('p'); info.textContent = `${labels[monitor.category]} · ${details(monitor)}`;
    const quiet = document.createElement('p'); quiet.className = 'text-sm text-forest-700'; quiet.textContent = monitor.quiet_hours_enabled ? `알림 중지 ${String(monitor.quiet_hours_start).slice(0,5)}–${String(monitor.quiet_hours_end).slice(0,5)} KST` : '알림 중지 시간 꺼짐';
    const actions = document.createElement('div'); actions.className = 'flex gap-3 mt-auto';
    [[active ? 'Pause' : 'Activate', async () => { await api(`/api/settings/${monitor.id}`, jsonOptions('PUT', { is_active: !active })); await load(); }],
     ['Edit', () => openModal(monitor.id)], ['Del', async () => { if (confirm('Sure?')) { await api(`/api/settings/${monitor.id}`, { method: 'DELETE' }); await load(); } }]]
      .forEach(([text, action]) => { const button = document.createElement('button'); button.className = 'brutal-btn px-4 py-2'; button.textContent = text; button.onclick = action; actions.appendChild(button); });
    card.append(heading, info, quiet, actions); container.appendChild(card);
  });
}

async function load() { try { monitors = await api('/api/settings/all'); render(); } catch (error) { toast(error.message, 'error'); } }

async function save(event) {
  event.preventDefault(); if (!byId('settings-form').reportValidity()) return;
  const payload = formData(); if (payload.category === 'ktx' && !payload.options.seat_classes.length) return toast('Select at least one seat class', 'error');
  try { const id = byId('monitor_id').value; await api(id ? `/api/settings/${id}` : '/api/settings', jsonOptions('PUT', payload)); closeModal(); await load(); toast('Saved'); }
  catch (error) { toast(error.message, 'error'); }
}

const picker = createStationPicker((target, station) => { byId(`ktx_${target}`).value = station.name; byId(`ktx_${target}_code`).value = station.code; });
document.addEventListener('DOMContentLoaded', async () => {
  await loadCatalogs(); await load();
  document.querySelectorAll('[data-category]').forEach(button => { button.onclick = () => setCategory(button.dataset.category); button.ondragstart = event => event.dataTransfer.setData('text/plain', button.dataset.category); });
  const dropzone = byId('category-dropzone'); dropzone.ondragover = event => event.preventDefault(); dropzone.ondrop = event => { event.preventDefault(); setCategory(event.dataTransfer.getData('text/plain')); };
  document.querySelectorAll('[data-station-target]').forEach(button => button.onclick = () => picker.open(button.dataset.stationTarget));
  ['departure','arrival'].forEach(target => byId(`ktx_${target}`).onclick = () => picker.open(target));
  document.querySelectorAll('input[name="date_mode"]').forEach(input => input.onchange = () => setDateMode(input.value));
  byId('quiet_hours_enabled').onchange = event => setQuietEnabled(event.target.checked);
  byId('btn-add-setting').onclick = () => openModal(); byId('btn-close-modal').onclick = closeModal; byId('btn-cancel-modal-footer').onclick = closeModal; byId('btn-save-setting').onclick = save;
  byId('btn-test').onclick = async () => { try { const result = await api('/api/check?test=true', { method: 'POST' }); toast(result.status === 'running' ? 'Check already running' : 'Check queued'); } catch (error) { toast(error.message, 'error'); } };
  byId('btn-clear-all-history').onclick = async () => { if (confirm('Clear all?')) { await api('/api/history', { method: 'DELETE' }); toast('Cleared'); } };
  byId('btn-clear-history').onclick = async () => { const id = byId('monitor_id').value; if (id && confirm('Sure?')) { await api(`/api/settings/${id}/history`, { method: 'DELETE' }); toast('Cleared'); } };
  byId('btn-quick-search-page').onclick = () => window.open('search.html', '_blank');
  byId('btn-select-all-parks').onclick = () => { const boxes = document.querySelectorAll('input[name="selected_parks"]'); const all = Array.from(boxes).every(box => box.checked); boxes.forEach(box => { box.checked = !all; }); };
});
