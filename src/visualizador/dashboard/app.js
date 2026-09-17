// Political Sentinel — Dashboard Logic
let dashboardData = null;
let planoChartInstance = null;
let radarChartInstance = null;

// Colores por defecto para partidos no registrados
const DEFAULT_COLOR = "#94a3b8";

document.addEventListener("DOMContentLoaded", async () => {
  setupTabs();
  await loadDashboardData();
  setupFilters();
  renderPlano2D();
  renderRadar6D();
  renderLeyesCards();
  renderBancadasTable();
});

// GESTIÓN DE PESTAÑAS
function setupTabs() {
  const buttons = document.querySelectorAll(".nav-btn");
  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      buttons.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));
      
      btn.classList.add("active");
      const targetId = `tab-${btn.dataset.tab}`;
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");
    });
  });
}

// CARGA DE DATOS
async function loadDashboardData() {
  try {
    const response = await fetch("data_dashboard.json");
    if (!response.ok) throw new Error("No se pudo cargar data_dashboard.json");
    dashboardData = await response.json();
    renderStats();
  } catch (error) {
    console.error("Error al cargar datos:", error);
    document.querySelector(".main-container").innerHTML = `
      <div style="background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; padding: 1.5rem; border-radius: 8px;">
        <h3>Error de Carga</h3>
        <p>No se pudo cargar el archivo <code>data_dashboard.json</code>. Asegúrate de ejecutar <code>python -m src.motor.generar_datos_dashboard</code> para compilar el dataset.</p>
      </div>
    `;
  }
}

// RENDERIZADO DE ESTADÍSTICAS
function renderStats() {
  if (!dashboardData || !dashboardData.resumen) return;
  const r = dashboardData.resumen;
  const bar = document.getElementById("statsBar");
  bar.innerHTML = `
    <div class="stat-item">
      <div class="stat-value">${r.total_leyes}</div>
      <div class="stat-label">Leyes Evaluadas</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${r.total_parlamentarios}</div>
      <div class="stat-label">Parlamentarios</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${r.total_bancadas}</div>
      <div class="stat-label">Bancadas</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${r.votaciones_procesadas}</div>
      <div class="stat-label">Votaciones Oficiales</div>
    </div>
  `;
}

// FILTROS
function setupFilters() {
  if (!dashboardData) return;
  const selectPartido = document.getElementById("filtroPartido");
  const bancadas = [...new Set(dashboardData.parlamentarios_posicionados.map(p => p.parlamentario.bancada || p.parlamentario.partido))].sort();
  
  bancadas.forEach(banc => {
    const opt = document.createElement("option");
    opt.value = banc;
    opt.textContent = banc;
    selectPartido.appendChild(opt);
  });

  document.getElementById("filtroCamara").addEventListener("change", updatePlanoChart);
  document.getElementById("filtroPartido").addEventListener("change", updatePlanoChart);
  document.getElementById("checkElipses").addEventListener("change", updatePlanoChart);
  document.getElementById("checkNombres").addEventListener("change", updatePlanoChart);
}

// TAB 1: PLANO CARTESIANO 2D
function getFilteredParlamentarios() {
  if (!dashboardData) return [];
  const camara = document.getElementById("filtroCamara").value;
  const partido = document.getElementById("filtroPartido").value;

  return dashboardData.parlamentarios_posicionados.filter(p => {
    const matchCamara = (camara === "TODAS") || (p.parlamentario.camara === camara);
    const matchPart = (partido === "TODOS") || ((p.parlamentario.bancada || p.parlamentario.partido) === partido);
    return matchCamara && matchPart;
  });
}

function renderPlano2D() {
  const ctx = document.getElementById("planoChart").getContext("2d");
  const filtrados = getFilteredParlamentarios();
  const showElipses = document.getElementById("checkElipses").checked;

  const datasets = [];

  // 1. Puntos de parlamentarios
  const parlPoints = filtrados.map(p => {
    const col = (dashboardData.colores_bancadas && dashboardData.colores_bancadas[p.parlamentario.bancada]) || DEFAULT_COLOR;
    return {
      x: p.x,
      y: p.y,
      raw: p,
      backgroundColor: col
    };
  });

  datasets.push({
    label: "Parlamentarios",
    data: parlPoints,
    pointRadius: 6,
    pointHoverRadius: 9,
    pointBackgroundColor: parlPoints.map(pt => pt.backgroundColor),
    pointBorderColor: "#ffffff",
    pointBorderWidth: 1.5,
  });

  // 2. Centroides de bancada
  const selectedPartido = document.getElementById("filtroPartido").value;
  const bancadasFiltradas = dashboardData.bancadas_metricas.filter(b => {
    return (selectedPartido === "TODOS") || (b.bancada === selectedPartido);
  });

  const centroidesData = bancadasFiltradas.map(b => {
    const col = (dashboardData.colores_bancadas && dashboardData.colores_bancadas[b.bancada]) || DEFAULT_COLOR;
    return {
      x: b.x_centroide,
      y: b.y_centroide,
      bancada: b,
      color: col
    };
  });

  datasets.push({
    label: "Centroides de Bancada (Promedio)",
    data: centroidesData,
    pointStyle: "rectRot",
    pointRadius: 9,
    pointHoverRadius: 12,
    pointBackgroundColor: centroidesData.map(c => c.color),
    pointBorderColor: "#ffffff",
    pointBorderWidth: 2,
  });

  // Plugin de fondo de cuadrantes
  const quadrantBackgroundPlugin = {
    id: "quadrantBackground",
    beforeDraw(chart) {
      const { ctx, chartArea: { left, top, right, bottom, width, height }, scales: { x, y } } = chart;
      const xZero = x.getPixelForValue(0);
      const yZero = y.getPixelForValue(0);

      // Cuadrante I: X > 0, Y > 0 (Top-Right)
      ctx.fillStyle = "rgba(16, 185, 129, 0.04)";
      ctx.fillRect(xZero, top, right - xZero, yZero - top);

      // Cuadrante II: X <= 0, Y > 0 (Top-Left)
      ctx.fillStyle = "rgba(245, 158, 11, 0.04)";
      ctx.fillRect(left, top, xZero - left, yZero - top);

      // Cuadrante III: X <= 0, Y <= 0 (Bottom-Left)
      ctx.fillStyle = "rgba(59, 130, 246, 0.04)";
      ctx.fillRect(left, yZero, xZero - left, bottom - yZero);

      // Cuadrante IV: X > 0, Y <= 0 (Bottom-Right)
      ctx.fillStyle = "rgba(239, 68, 68, 0.04)";
      ctx.fillRect(xZero, yZero, right - xZero, bottom - yZero);

      // Ejes centrales ortogonales
      ctx.save();
      ctx.strokeStyle = "rgba(148, 163, 184, 0.4)";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);

      // Eje vertical (X = 0)
      ctx.beginPath();
      ctx.moveTo(xZero, top);
      ctx.lineTo(xZero, bottom);
      ctx.stroke();

      // Eje horizontal (Y = 0)
      ctx.beginPath();
      ctx.moveTo(left, yZero);
      ctx.lineTo(right, yZero);
      ctx.stroke();

      // Dibujar elipses de dispersión partidaria si está activo
      if (document.getElementById("checkElipses").checked) {
        bancadasFiltradas.forEach(b => {
          if (b.total_miembros > 1 && b.elipse_semieje_mayor > 0.02) {
            const cx = x.getPixelForValue(b.x_centroide);
            const cy = y.getPixelForValue(b.y_centroide);
            const rx = Math.abs(x.getPixelForValue(b.elipse_semieje_mayor) - x.getPixelForValue(0));
            const ry = Math.abs(y.getPixelForValue(b.elipse_semieje_menor) - y.getPixelForValue(0));
            const rotRad = (b.elipse_angulo_grados * Math.PI) / 180;
            const col = (dashboardData.colores_bancadas && dashboardData.colores_bancadas[b.bancada]) || DEFAULT_COLOR;

            ctx.save();
            ctx.beginPath();
            ctx.setLineDash([]);
            ctx.strokeStyle = col;
            ctx.lineWidth = 1.8;
            ctx.ellipse(cx, cy, rx, ry, rotRad, 0, 2 * Math.PI);
            ctx.stroke();
            ctx.fillStyle = col.replace(")", ", 0.1)").replace("rgb", "rgba").replace("#", "");
            ctx.restore();
          }
        });
      }

      ctx.restore();
    }
  };

  planoChartInstance = new Chart(ctx, {
    type: "scatter",
    data: { datasets },
    plugins: [quadrantBackgroundPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          min: -1.05,
          max: 1.05,
          title: {
            display: true,
            text: "← Menor Intervención / Pro-Mercado | Eje X: Carga e Intervención Económica | Mayor Extracción y Carga Fiscal →",
            color: "#94a3b8",
            font: { size: 12, weight: "bold" }
          },
          grid: { color: "rgba(51, 65, 85, 0.4)" },
          ticks: { color: "#94a3b8" }
        },
        y: {
          min: -1.05,
          max: 1.05,
          title: {
            display: true,
            text: "← Menor Gasto Social / Focalización | Eje Y: Bienestar y Protección Social | Mayor Protección y Derechos →",
            color: "#94a3b8",
            font: { size: 12, weight: "bold" }
          },
          grid: { color: "rgba(51, 65, 85, 0.4)" },
          ticks: { color: "#94a3b8" }
        }
      },
      plugins: {
        legend: {
          labels: { color: "#f8fafc" }
        },
        tooltip: {
          callbacks: {
            label(context) {
              const raw = context.raw;
              if (raw.raw) {
                const p = raw.raw;
                return `${p.parlamentario.nombre_completo} (${p.parlamentario.partido}) | X: ${p.x}, Y: ${p.y} [${p.cuadrante}]`;
              }
              if (raw.bancada) {
                const b = raw.bancada;
                return `Bancada: ${b.bancada} (Centroide: X=${b.x_centroide}, Y=${b.y_centroide}, Disciplina: ${b.disciplina_id})`;
              }
              return "";
            }
          }
        }
      },
      onClick(event, elements) {
        if (elements.length > 0) {
          const el = elements[0];
          const dataItem = planoChartInstance.data.datasets[el.datasetIndex].data[el.index];
          if (dataItem.raw) {
            mostrarDetalleParlamentario(dataItem.raw);
          }
        }
      }
    }
  });
}

function updatePlanoChart() {
  if (!planoChartInstance) return;
  planoChartInstance.destroy();
  renderPlano2D();
}

function mostrarDetalleParlamentario(pos) {
  const p = pos.parlamentario;
  const badge = document.getElementById("sideBadge");
  const content = document.getElementById("sideContent");

  badge.textContent = pos.cuadrante;
  badge.className = `badge q-${pos.cuadrante.toLowerCase()}`;

  content.innerHTML = `
    <div class="parl-card">
      <h4>${p.nombre_completo}</h4>
      <div class="parl-meta">
        <strong>${p.camara}</strong> &bull; ${p.partido}${p.bancada && p.bancada !== p.partido ? ` &bull; Bancada: ${p.bancada}` : ""} &bull; ${p.distrito_o_circunscripcion || ""}
      </div>

      <div class="coord-box">
        <div class="coord-item">
          <span>Eje X (Carga/Intervención):</span>
          <span class="coord-val" style="color: ${pos.x > 0 ? '#ef4444' : '#3b82f6'}">${pos.x}</span>
        </div>
        <div class="coord-item">
          <span>Eje Y (Bienestar/Protección):</span>
          <span class="coord-val" style="color: ${pos.y > 0 ? '#10b981' : '#f59e0b'}">${pos.y}</span>
        </div>
        <div class="coord-item">
          <span>Cuadrante:</span>
          <strong>${pos.nombre_cuadrante}</strong>
        </div>
        <div class="coord-item">
          <span>Votaciones Computadas:</span>
          <span>${pos.total_votaciones_computadas}</span>
        </div>
      </div>

      <div style="font-size: 0.85rem; color: #94a3b8; line-height: 1.4;">
        <p><strong>Diagnóstico de Comportamiento:</strong></p>
        <p>${obtenerDiagnosticoCuadrante(pos.x, pos.y)}</p>
      </div>
    </div>
  `;
}

function obtenerDiagnosticoCuadrante(x, y) {
  if (x > 0 && y > 0) {
    return "Votaciones afirmativas en leyes de expansión de derechos y subsidios, respaldando además las reformas y tributos para su financiamiento fiscal.";
  } else if (x <= 0 && y > 0) {
    return "Votaciones afirmativas sistemáticas en subsidios y bonos directos, pero oposición o rechazo a los impuestos y costos para financiarlos (asistencialismo no financiado).";
  } else if (x <= 0 && y <= 0) {
    return "Votaciones contrarias a alzas impositivas, costos operacionales a empresas y burocracia, priorizando el mercado y focalización mínima de recursos.";
  } else {
    return "Votaciones a favor de tributos o exigencias regulatorias que imponen fricción al sector privado sin asociarse a beneficios o derechos sociales directos.";
  }
}

// TABLA DE BANCADAS
function renderBancadasTable() {
  if (!dashboardData || !dashboardData.bancadas_metricas) return;
  const tbody = document.querySelector("#tablaBancadas tbody");
  tbody.innerHTML = "";

  dashboardData.bancadas_metricas
    .sort((a, b) => b.total_miembros - a.total_miembros)
    .forEach(b => {
      const col = (dashboardData.colores_bancadas && dashboardData.colores_bancadas[b.bancada]) || DEFAULT_COLOR;
      const row = document.createElement("tr");
      
      const cuad = (b.x_centroide > 0 ? (b.y_centroide > 0 ? "I" : "IV") : (b.y_centroide > 0 ? "II" : "III"));
      const disp = Math.sqrt(Math.pow(b.sigma_x, 2) + Math.pow(b.sigma_y, 2)).toFixed(3);

      row.innerHTML = `
        <td><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${col};margin-right:8px;"></span><strong>${b.bancada}</strong></td>
        <td>${b.total_miembros}</td>
        <td><code>(${b.x_centroide}, ${b.y_centroide})</code></td>
        <td><span class="q-badge q${cuad.toLowerCase()}">Cuadrante ${cuad}</span></td>
        <td><strong style="color: ${b.disciplina_id > 0.8 ? '#10b981' : '#f59e0b'}">${(b.disciplina_id * 100).toFixed(1)}%</strong></td>
        <td>&sigma; = ${disp}</td>
      `;
      tbody.appendChild(row);
    });
}

// TAB 2: RADAR 6D
const EJES_RADAR = ["d1_transferencias", "d2_bienes_publicos", "d3_derechos_laborales", "d4_carga_fiscal", "d5_costos_privados", "d6_burocracia"];
const LABELS_RADAR = ["D1: Transferencias", "D2: Bienes Públicos", "D3: Derechos Laborales", "D4: Carga Fiscal", "D5: Costos Privados", "D6: Burocracia"];

function vectorAValores(vi) {
  return EJES_RADAR.map(eje => vi[eje]);
}

function renderRadar6D() {
  if (!dashboardData || !dashboardData.leyes) return;

  // Modo "Ver una Ley"
  const selectLey = document.getElementById("selectLeyRadar");
  selectLey.innerHTML = "";
  dashboardData.leyes.forEach((ley, idx) => {
    const opt = document.createElement("option");
    opt.value = ley.boletin;
    opt.textContent = `[${ley.boletin}] ${ley.titulo}`;
    if (idx === 0) opt.selected = true;
    selectLey.appendChild(opt);
  });
  selectLey.addEventListener("change", () => updateRadarChart(selectLey.value));

  // Modo "Comparar": cada lado puede ser un parlamentario, una bancada, una ley,
  // o el promedio de todas las leyes.
  setupComparador("A", "parlamentario");
  setupComparador("B", "promedio");

  // Toggle de modo
  const modeButtons = document.querySelectorAll(".mode-btn");
  modeButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      modeButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const esLey = btn.dataset.modo === "ley";
      document.getElementById("radarControlLey").style.display = esLey ? "" : "none";
      document.getElementById("radarControlComparar").style.display = esLey ? "none" : "";
      document.getElementById("votosDetailContainer").style.display = esLey ? "none" : "";
      if (esLey) {
        updateRadarChart(selectLey.value);
      } else {
        renderComparacion();
      }
    });
  });

  updateRadarChart(dashboardData.leyes[0].boletin);
}

function setupComparador(lado, tipoDefault) {
  const tipoSelect = document.getElementById(`tipoLado${lado}`);
  const valorSelect = document.getElementById(`valorLado${lado}`);
  tipoSelect.value = tipoDefault;
  poblarSelectorValor(tipoDefault, valorSelect);
  tipoSelect.addEventListener("change", () => {
    poblarSelectorValor(tipoSelect.value, valorSelect);
    renderComparacion();
  });
  valorSelect.addEventListener("change", renderComparacion);
}

function poblarSelectorValor(tipo, selectEl) {
  selectEl.innerHTML = "";
  selectEl.disabled = false;

  if (tipo === "promedio") {
    const opt = document.createElement("option");
    opt.value = "__promedio__";
    opt.textContent = "Promedio de todas las leyes evaluadas";
    selectEl.appendChild(opt);
    selectEl.disabled = true;
    return;
  }

  if (tipo === "parlamentario") {
    [...(dashboardData.perfiles_radar_parlamentarios || [])]
      .sort((a, b) => a.parlamentario.nombre_completo.localeCompare(b.parlamentario.nombre_completo))
      .forEach(pf => {
        const opt = document.createElement("option");
        opt.value = pf.parlamentario.id;
        opt.textContent = `${pf.parlamentario.nombre_completo} (${pf.parlamentario.partido})`;
        selectEl.appendChild(opt);
      });
    return;
  }

  if (tipo === "bancada") {
    [...(dashboardData.perfiles_radar_bancadas || [])]
      .sort((a, b) => b.total_miembros - a.total_miembros)
      .forEach(pb => {
        const opt = document.createElement("option");
        opt.value = pb.bancada;
        opt.textContent = `${pb.bancada} (${pb.total_miembros} en catálogo)`;
        selectEl.appendChild(opt);
      });
    return;
  }

  if (tipo === "ley") {
    dashboardData.leyes.forEach(ley => {
      const opt = document.createElement("option");
      opt.value = ley.boletin;
      opt.textContent = `[${ley.boletin}] ${ley.titulo}`;
      selectEl.appendChild(opt);
    });
  }
}

function resolverEntidadRadar(tipo, valor) {
  if (tipo === "promedio") {
    return {
      vector: dashboardData.perfil_promedio_leyes,
      etiqueta: "Promedio de todas las leyes",
      detalle: "Promedio simple del vector de impacto de las leyes evaluadas.",
      esParlamentario: false,
    };
  }
  if (tipo === "parlamentario") {
    const pf = (dashboardData.perfiles_radar_parlamentarios || []).find(x => x.parlamentario.id === valor);
    if (!pf) return null;
    const p = pf.parlamentario;
    const bancadaTxt = p.bancada && p.bancada !== p.partido ? ` &bull; Bancada: ${p.bancada}` : "";
    return {
      vector: pf.vector_promedio,
      etiqueta: p.nombre_completo,
      detalle: `${p.camara} &bull; ${p.partido}${bancadaTxt} &bull; ${pf.total_votaciones_computadas}/${dashboardData.resumen.total_leyes} votaciones computadas`,
      esParlamentario: true,
      parlamentarioId: p.id,
    };
  }
  if (tipo === "bancada") {
    const pb = (dashboardData.perfiles_radar_bancadas || []).find(x => x.bancada === valor);
    if (!pb) return null;
    return {
      vector: pb.vector_promedio,
      etiqueta: pb.bancada,
      detalle: `Bancada &bull; ${pb.total_miembros} parlamentarios en el catálogo`,
      esParlamentario: false,
    };
  }
  if (tipo === "ley") {
    const ley = dashboardData.leyes.find(l => l.boletin === valor);
    if (!ley) return null;
    return {
      vector: ley.vector_impacto,
      etiqueta: `[${ley.boletin}] ${ley.titulo}`,
      detalle: ley.justificacion,
      esParlamentario: false,
    };
  }
  return null;
}

function renderComparacion() {
  const tipoA = document.getElementById("tipoLadoA").value;
  const valorA = document.getElementById("valorLadoA").value;
  const tipoB = document.getElementById("tipoLadoB").value;
  const valorB = document.getElementById("valorLadoB").value;

  const entA = resolverEntidadRadar(tipoA, valorA);
  const entB = resolverEntidadRadar(tipoB, valorB);
  if (!entA) return;

  const card = document.getElementById("leyInfoCard");
  card.innerHTML = `
    <h4 style="color:#10b981;">${entA.etiqueta}</h4>
    <p>${entA.detalle}</p>
    ${entB ? `<h4 style="color:#94a3b8;">${entB.etiqueta}</h4><p>${entB.detalle}</p>` : ""}
    <p style="font-size:0.8rem;">Cada eje es el promedio de <code>voto × valor_del_eje</code> en las leyes votadas (o el vector propio, si el lado es una ley). Cuanto más se parezcan las dos formas, más alineados están.</p>
  `;

  const datasets = [{
    label: entA.etiqueta,
    data: vectorAValores(entA.vector),
    backgroundColor: "rgba(16, 185, 129, 0.25)",
    borderColor: "#10b981",
    pointBackgroundColor: "#34d399",
    pointBorderColor: "#ffffff",
    borderWidth: 2.5,
  }];
  if (entB) {
    datasets.push({
      label: entB.etiqueta,
      data: vectorAValores(entB.vector),
      backgroundColor: "rgba(148, 163, 184, 0.12)",
      borderColor: "#94a3b8",
      pointBackgroundColor: "#cbd5e1",
      pointBorderColor: "#ffffff",
      borderWidth: 2,
      borderDash: [5, 4],
    });
  }

  const ctx = document.getElementById("radarChart").getContext("2d");
  if (radarChartInstance) radarChartInstance.destroy();
  radarChartInstance = new Chart(ctx, {
    type: "radar",
    data: { labels: LABELS_RADAR, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: -1.0,
          max: 1.0,
          ticks: { stepSize: 0.5, color: "#94a3b8", backdropColor: "transparent" },
          grid: { color: "rgba(51, 65, 85, 0.6)" },
          angleLines: { color: "rgba(51, 65, 85, 0.6)" },
          pointLabels: { color: "#f8fafc", font: { size: 12, weight: "bold" } }
        }
      },
      plugins: { legend: { labels: { color: "#f8fafc" } } }
    }
  });

  renderTablaVotos([entA, entB].filter(e => e && e.esParlamentario));
}

function updateRadarChart(boletin) {
  const ley = dashboardData.leyes.find(l => l.boletin === boletin);
  if (!ley) return;

  // Actualizar tarjeta lateral de la ley
  const card = document.getElementById("leyInfoCard");
  card.innerHTML = `
    <h4>${ley.titulo}</h4>
    <p><span class="boletin-tag">Boletín: ${ley.boletin}</span></p>
    <p><strong>Sectores Afectados:</strong> ${ley.sectores_afectados.join(", ")}</p>
    ${ley.recaudacion_estimada_clp ? `<p><strong>Recaudación Estimada:</strong> CLP $${(ley.recaudacion_estimada_clp / 1e12).toFixed(2)} billones/año</p>` : ''}
    ${ley.costo_fiscal_anual_clp ? `<p><strong>Costo Fiscal Anual:</strong> CLP $${(ley.costo_fiscal_anual_clp / 1e12).toFixed(2)} billones/año</p>` : ''}
    ${ley.beneficiarios_estimados ? `<p><strong>Beneficiarios Estimados:</strong> ${ley.beneficiarios_estimados.toLocaleString()}</p>` : ''}
    <p><strong>Justificación Técnica:</strong><br>${ley.justificacion}</p>
  `;

  const vi = ley.vector_impacto;
  const labels = [
    "D1: Transferencias",
    "D2: Bienes Públicos",
    "D3: Derechos Laborales",
    "D4: Carga Fiscal",
    "D5: Costos Privados",
    "D6: Burocracia"
  ];
  const dataValues = [
    vi.d1_transferencias,
    vi.d2_bienes_publicos,
    vi.d3_derechos_laborales,
    vi.d4_carga_fiscal,
    vi.d5_costos_privados,
    vi.d6_burocracia
  ];

  const ctx = document.getElementById("radarChart").getContext("2d");
  if (radarChartInstance) radarChartInstance.destroy();

  radarChartInstance = new Chart(ctx, {
    type: "radar",
    data: {
      labels,
      datasets: [{
        label: `Vector de Impacto (L): ${ley.boletin}`,
        data: dataValues,
        backgroundColor: "rgba(59, 130, 246, 0.25)",
        borderColor: "#3b82f6",
        pointBackgroundColor: "#60a5fa",
        pointBorderColor: "#ffffff",
        pointHoverBackgroundColor: "#ffffff",
        pointHoverBorderColor: "#3b82f6",
        borderWidth: 2.5,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: -1.0,
          max: 1.0,
          ticks: {
            stepSize: 0.5,
            color: "#94a3b8",
            backdropColor: "transparent"
          },
          grid: { color: "rgba(51, 65, 85, 0.6)" },
          angleLines: { color: "rgba(51, 65, 85, 0.6)" },
          pointLabels: {
            color: "#f8fafc",
            font: { size: 12, weight: "bold" }
          }
        }
      },
      plugins: {
        legend: { labels: { color: "#f8fafc" } }
      }
    }
  });
}

function renderTablaVotos(entidades) {
  const container = document.getElementById("votosDetailContainer");
  const thead = document.querySelector("#tablaVotosParlamentario thead tr");
  const tbody = document.querySelector("#tablaVotosParlamentario tbody");

  if (!dashboardData || !dashboardData.votos_por_parlamentario || entidades.length === 0) {
    container.style.display = "none";
    return;
  }

  thead.innerHTML = "<th>Boletín</th><th>Ley</th>" + entidades.map(e => `<th>${e.etiqueta}</th>`).join("");
  tbody.innerHTML = "";

  dashboardData.leyes.forEach(ley => {
    const celdas = entidades.map(e => {
      const opcion = (dashboardData.votos_por_parlamentario[e.parlamentarioId] || {})[ley.boletin] || "Sin registro / no computa";
      const colorVoto = opcion === "AFIRMATIVO" ? "#34d399" : opcion === "EN CONTRA" ? "#f87171" : opcion === "ABSTENCION" ? "#fbbf24" : "#94a3b8";
      return `<td><strong style="color:${colorVoto}">${opcion}</strong></td>`;
    }).join("");
    const row = document.createElement("tr");
    row.innerHTML = `<td><span class="boletin-tag">${ley.boletin}</span></td><td>${ley.titulo}</td>${celdas}`;
    tbody.appendChild(row);
  });

  container.style.display = "";
}

// TAB 3: CATALOGO DE LEYES
function renderLeyesCards() {
  if (!dashboardData || !dashboardData.leyes) return;
  const container = document.getElementById("cardsLeyes");
  container.innerHTML = "";

  dashboardData.leyes.forEach(ley => {
    const vi = ley.vector_impacto;
    const card = document.createElement("div");
    card.className = "ley-card";
    card.innerHTML = `
      <span class="boletin-tag">Boletín ${ley.boletin}</span>
      <h3>${ley.titulo}</h3>
      <p style="color:#94a3b8; font-size:0.85rem; margin-bottom: 0.75rem;"><strong>Sectores:</strong> ${ley.sectores_afectados.join(", ")}</p>
      
      <div class="vector-pill-list">
        <div class="vector-pill"><span>D1 Transferencias:</span> <strong>${vi.d1_transferencias > 0 ? '+' : ''}${vi.d1_transferencias}</strong></div>
        <div class="vector-pill"><span>D2 Bienes Públicos:</span> <strong>${vi.d2_bienes_publicos > 0 ? '+' : ''}${vi.d2_bienes_publicos}</strong></div>
        <div class="vector-pill"><span>D3 Derechos Laborales:</span> <strong>${vi.d3_derechos_laborales > 0 ? '+' : ''}${vi.d3_derechos_laborales}</strong></div>
        <div class="vector-pill"><span>D4 Carga Fiscal:</span> <strong>${vi.d4_carga_fiscal > 0 ? '+' : ''}${vi.d4_carga_fiscal}</strong></div>
        <div class="vector-pill"><span>D5 Costos Privados:</span> <strong>${vi.d5_costos_privados > 0 ? '+' : ''}${vi.d5_costos_privados}</strong></div>
        <div class="vector-pill"><span>D6 Burocracia:</span> <strong>${vi.d6_burocracia > 0 ? '+' : ''}${vi.d6_burocracia}</strong></div>
      </div>

      <p style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.4; margin-top: auto;">${ley.justificacion}</p>
    `;
    container.appendChild(card);
  });
}
