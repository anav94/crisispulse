const map = L.map('map', {
  worldCopyJump: false,
  inertia: false,
  maxBounds: [[-85, -180], [85, 180]],
  maxBoundsViscosity: 1.0
}).setView([20, 0], 2);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18,
  noWrap: true
}).addTo(map);

const clusters = L.markerClusterGroup({
  showCoverageOnHover: false,
  maxClusterRadius: 40
});
map.addLayer(clusters);

const tbody = document.querySelector('#incidents tbody');
const statusEl = document.querySelector('#status');

let markerCount = 0;
function updateStatus(rowCount) {
  statusEl.textContent = `Rows: ${rowCount}  •  Markers: ${markerCount}`;
}

function addRow(inc) {
  const tr = document.createElement('tr');
  const when = new Date(inc.occurred_ts*1000).toLocaleString();
  tr.innerHTML = `<td>${inc.id}</td><td>${inc.source}</td><td>${inc.title || ''}</td><td>${inc.magnitude ?? ''}</td><td>${(inc.severity*100).toFixed(0)}%</td><td>${when}</td>`;
  tbody.prepend(tr);
  while (tbody.rows.length > 300) tbody.deleteRow(300);
  updateStatus(tbody.rows.length);
}

function addMarker(inc) {
  if (inc.lat == null || inc.lon == null) return;
  const radius = 4 + (inc.severity * 8);
  let color = '#00cc44'; // green
  if (inc.severity > 0.7) {
    color = '#cc0000'; // red
  } else if (inc.severity > 0.4) {
    color = '#ffcc00'; // yellow
  }
  const m = L.circleMarker([inc.lat, inc.lon], {
    radius: radius,
    color: color,
    fillColor: color,
    fillOpacity: 0.8
  });
  const gm = `https://www.google.com/maps?q=${inc.lat},${inc.lon}`;
  m.bindPopup(`<b>${inc.source}</b><br/>${inc.title || ''}<br/>mag: ${inc.magnitude ?? ''}<br/>sev: ${(inc.severity*100).toFixed(0)}%<br/><a href="${gm}" target="_blank">Open in Maps</a>`);
  clusters.addLayer(m);
  markerCount += 1;
  updateStatus(tbody.rows.length);
}

async function bootstrap() {
  const initial = await fetch('/api/incidents?limit=200').then(r => r.json());
  let lastId = 0;
  initial.reverse().forEach(inc => { addRow(inc); addMarker(inc); lastId = Math.max(lastId, inc.id); });
  if (clusters.getLayers().length > 0) {
    map.fitBounds(clusters.getBounds().pad(0.2));
  }
  const es = new EventSource(`/stream?last_id=${lastId}`);
  es.addEventListener('incident', (ev) => {
    const data = JSON.parse(ev.data);
    addRow(data);
    addMarker(data);
  });
}
bootstrap();
