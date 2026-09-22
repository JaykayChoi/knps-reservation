import { api } from './api.js';

const byId = id => document.getElementById(id);
const button = byId('btn-search');
const results = byId('results-container');

function formatDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function weekdayDates(weeks, days) {
  const values = [];
  const numbers = new Set(days.map(day => ({ Sun: 0, Mon: 1, Tue: 2, Wed: 3,
    Thu: 4, Fri: 5, Sat: 6 })[day]));
  const today = new Date();
  for (let offset = 0; offset < weeks * 7; offset += 1) {
    const candidate = new Date(today.getFullYear(), today.getMonth(), today.getDate() + offset);
    if (numbers.has(candidate.getDay())) values.push(formatDate(candidate));
  }
  return values;
}

function rangeDates(start, end) {
  const values = [];
  const current = new Date(`${start}T00:00:00`);
  const stop = new Date(`${end}T00:00:00`);
  while (current <= stop && values.length < 120) {
    values.push(formatDate(current));
    current.setDate(current.getDate() + 1);
  }
  return values;
}

function text(tag, value, className = '') {
  const element = document.createElement(tag);
  element.className = className; element.textContent = value;
  return element;
}

function renderRows(rows) {
  results.replaceChildren();
  if (!rows.length) {
    results.appendChild(text('div', 'No availability found', 'brutal-card p-12 text-center bg-white font-serif text-2xl font-bold'));
    return;
  }
  const groups = new Map();
  rows.forEach(row => {
    const key = row.park_name || 'Unknown park';
    groups.set(key, [...(groups.get(key) || []), row]);
  });
  groups.forEach((sites, park) => {
    const card = document.createElement('section'); card.className = 'brutal-card overflow-hidden mb-8';
    card.appendChild(text('h2', `${park} · ${sites.length} items`, 'bg-forest-950 text-white p-4 font-serif text-xl font-bold'));
    sites.forEach(site => {
      const row = document.createElement('article'); row.className = 'p-4 border-b border-forest-950/10 bg-sand/20';
      row.append(text('h3', site.campsite_name || '', 'font-bold'),
        text('p', `${site.facility_type || ''} · ${site.date || ''}`, 'text-sm'),
        text('p', `예약 ${site.available_count || 0} · 대기 ${site.waiting_count || 0}`, 'font-bold mt-2'));
      card.appendChild(row);
    });
    results.appendChild(card);
  });
}

document.querySelectorAll('input[name="date_mode"]').forEach(input => {
  input.addEventListener('change', () => {
    byId('weekday-ui').classList.toggle('hidden', input.value !== 'weekday');
    byId('absolute-ui').classList.toggle('hidden', input.value !== 'absolute');
  });
});

button.addEventListener('click', async () => {
  const mode = document.querySelector('input[name="date_mode"]:checked').value;
  let dates;
  if (mode === 'weekday') {
    const days = Array.from(document.querySelectorAll('input[name="days"]:checked'), input => input.value);
    if (!days.length) return window.alert('Select days.');
    dates = weekdayDates(Number(byId('weeks_ahead').value), days);
  } else {
    const start = byId('start_date').value, end = byId('end_date').value;
    if (!start || !end || start > end) return window.alert('Select a valid date range.');
    dates = rangeDates(start, end);
  }
  button.disabled = true; button.textContent = 'Searching...'; results.textContent = 'Searching...';
  try {
    const query = new URLSearchParams({ dates: dates.join(','), types: byId('facility_type').value });
    renderRows(await api(`/api/search?${query}`));
  } catch (error) {
    results.replaceChildren(text('div', error.message, 'brutal-card p-8 bg-alert text-white'));
  } finally {
    button.disabled = false; button.textContent = 'Search Now';
  }
});
