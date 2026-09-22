import { api } from './api.js';

const areaLabels = { '0': '서울', '1': '경기', '2': '강원', '3': '충북', '4': '충남',
  '7': '전북', '8': '전남', '5': '경북', '6': '경남', '9': '광역시', all: '전체' };

function initials(name) {
  const chars = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ';
  return Array.from(name).map(char => {
    const offset = char.charCodeAt(0) - 0xAC00;
    return offset >= 0 && offset < 11172 ? chars[Math.floor(offset / 588)] : char;
  }).join('');
}

export function createStationPicker(onSelect) {
  const modal = document.getElementById('station-modal');
  const search = document.getElementById('station-search');
  const grid = document.getElementById('station-grid');
  const regions = document.getElementById('station-regions');
  const recentBox = document.getElementById('recent-stations');
  let stations = [], target = null, tab = 'major', area = 'all';
  const recent = () => { try { return JSON.parse(localStorage.getItem('recentKtxStations') || '[]'); } catch { return []; } };
  const remember = station => localStorage.setItem('recentKtxStations', JSON.stringify(
    [station, ...recent().filter(item => item.code !== station.code)].slice(0, 8)));
  const button = (station, className = 'station-pill') => {
    const element = document.createElement('button');
    element.type = 'button'; element.className = className; element.textContent = station.name;
    element.onclick = () => { remember(station); onSelect(target, station); close(); };
    return element;
  };
  function render() {
    const query = search.value.trim().toLowerCase();
    document.querySelectorAll('[data-station-tab]').forEach(element =>
      element.setAttribute('aria-selected', String(element.dataset.stationTab === tab)));
    regions.classList.toggle('hidden', tab !== 'region'); regions.replaceChildren();
    if (tab === 'region') Object.entries(areaLabels).forEach(([code, label]) => {
      const element = document.createElement('button'); element.type = 'button';
      element.className = 'station-region border-2 border-forest-950 px-3 py-2 font-bold';
      element.textContent = label; element.setAttribute('aria-pressed', String(area === code));
      element.onclick = () => { area = code; render(); }; regions.appendChild(element);
    });
    recentBox.replaceChildren(...(recent().length ? recent() : stations.filter(s => s.major != null)
      .sort((a, b) => a.major - b.major).slice(0, 8)).map(s => button(s, 'station-pill py-2')));
    let visible = tab === 'major' ? stations.filter(s => s.major != null).sort((a, b) => a.major - b.major)
      : stations.filter(s => area === 'all' || s.area === area).sort((a, b) => a.name.localeCompare(b.name, 'ko'));
    if (query) visible = stations.filter(s => s.name.toLowerCase().includes(query) || initials(s.name).includes(query));
    grid.replaceChildren(...visible.map(s => button(s)));
    if (!visible.length) grid.textContent = '검색 결과가 없습니다.';
  }
  async function open(nextTarget) {
    target = nextTarget; tab = 'major'; area = 'all'; search.value = ''; modal.classList.remove('hidden');
    try { if (!stations.length) stations = await api('/api/ktx/stations'); render(); search.focus(); }
    catch { grid.textContent = '역 목록을 불러오지 못했습니다.'; }
  }
  function close() { modal.classList.add('hidden'); target = null; }
  search.addEventListener('input', render);
  document.getElementById('btn-close-station-modal').addEventListener('click', close);
  document.querySelectorAll('[data-station-tab]').forEach(element => element.addEventListener('click', () => {
    tab = element.dataset.stationTab; render();
  }));
  return { open, close };
}
