{% extends "base.html" %}
{% block conteudo %}

<style>
  .card-indicador {
    background-color: #fff;
    border-left: 5px solid #00009f;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.07);
    font-size: 1rem;
  }
  .valor-indicador {
    font-size: 1.5rem;
    font-weight: bold;
    color: #00009f;
    margin-top: 8px;
  }
  .card-clickable {
    cursor: pointer;
    transition: all 0.2s ease-in-out;
  }
  .card-clickable:hover {
    transform: scale(1.02);
    box-shadow: 0 0 15px rgba(0,0,0,0.1);
  }
  .detalhes-card {
    display: none;
    margin-top: 20px;
  }
  .titulo-detalhes {
    font-weight: bold;
    color: #00009f;
    margin-bottom: 10px;
  }
  canvas {
    max-width: 100%;
  }
</style>

<div class="container">
  <h2 class="mb-4">📊 Dashboard — Contas a Pagar</h2>

  <!-- Filtro -->
  <form method="get" class="mb-4 d-flex gap-3 align-items-end">
    <div>
      <label>De:</label>
      <input type="date" name="data_inicio" class="form-control" value="{{ data_inicio }}">
    </div>
    <div>
      <label>Até:</label>
      <input type="date" name="data_fim" class="form-control" value="{{ data_fim }}">
    </div>
    <button type="submit" class="btn btn-primary">🔍 Filtrar</button>
  </form>

  <!-- Indicadores -->
  <div class="row g-4 mb-4">
    <div class="col-md-3">
      <div class="card-indicador text-center">
        Previsto no Período
        <div class="valor-indicador">R$ {{ '{:,.2f}'.format(total_previsto).replace(',', 'X').replace('.', ',').replace('X', '.') }}</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="card-indicador text-center">
        Pago no Período
        <div class="valor-indicador">R$ {{ '{:,.2f}'.format(total_pago).replace(',', 'X').replace('.', ',').replace('X', '.') }}</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="card-indicador text-center">
        Saldo
        <div class="valor-indicador">R$ {{ '{:,.2f}'.format(saldo).replace(',', 'X').replace('.', ',').replace('X', '.') }}</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="card-indicador text-center card-clickable" onclick="toggleDetalhes('hoje')">
        Contas de Hoje
        <div class="valor-indicador">R$ {{ '{:,.2f}'.format(total_hoje).replace(',', 'X').replace('.', ',').replace('X', '.') }}</div>
      </div>
    </div>
    <div class="col-md-3 mt-3">
      <div class="card-indicador text-center card-clickable" onclick="toggleDetalhes('atraso')">
        Contas em Atraso
        <div class="valor-indicador text-danger">R$ {{ '{:,.2f}'.format(total_atraso).replace(',', 'X').replace('.', ',').replace('X', '.') }}</div>
      </div>
    </div>
    <div class="col-md-3 mt-3">
      <div class="card-indicador text-center">
        Necessidade de Caixa (Amanhã)
        <div class="valor-indicador {{ 'text-danger' if necessidade_caixa > 0 else 'text-success' }}">
          R$ {{ '{:,.2f}'.format(necessidade_caixa).replace(',', 'X').replace('.', ',').replace('X', '.') }}
        </div>
      </div>
    </div>
  </div>

  <!-- Detalhes: Hoje -->
  <div id="detalhes-hoje" class="detalhes-card">
    <div class="titulo-detalhes">📆 Contas com Vencimento Hoje</div>
    <ul class="list-group mb-3">
      {% for item in contas_hoje %}
        <li class="list-group-item d-flex justify-content-between">
          <div>{{ item[0] }} — {{ item[1] }}</div>
          <div>R$ {{ '{:,.2f}'.format(item[2]|float).replace(',', 'X').replace('.', ',').replace('X', '.') }}</div>
        </li>
      {% endfor %}
    </ul>
    <button class="btn btn-sm btn-secondary" onclick="toggleDetalhes('')">❌ Fechar</button>
  </div>

  <!-- Detalhes: Atraso -->
  <div id="detalhes-atraso" class="detalhes-card">
    <div class="titulo-detalhes">❌ Contas em Atraso</div>
    <ul class="list-group mb-3">
      {% for item in contas_atraso %}
        <li class="list-group-item d-flex justify-content-between">
          <div>{{ item[0] }} — {{ item[1] }}</div>
          <div>R$ {{ '{:,.2f}'.format(item[2]|float).replace(',', 'X').replace('.', ',').replace('X', '.') }}</div>
        </li>
      {% endfor %}
    </ul>
    <button class="btn btn-sm btn-secondary" onclick="toggleDetalhes('')">❌ Fechar</button>
  </div>

  <!-- Gráficos -->
  <div class="row mt-5">
    <div class="col-md-6">
      <canvas id="graficoStatus"></canvas>
    </div>
    <div class="col-md-6">
      <canvas id="graficoCategoria"></canvas>
    </div>
  </div>

  <div class="mt-5">
    <h5 class="text-center">📈 Contas a Pagar — Próximos Dias</h5>
    <canvas id="graficoLinha"></canvas>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  function toggleDetalhes(tipo) {
    document.getElementById("detalhes-hoje").style.display = tipo === 'hoje' ? 'block' : 'none';
    document.getElementById("detalhes-atraso").style.display = tipo === 'atraso' ? 'block' : 'none';
  }

  new Chart(document.getElementById("graficoStatus"), {
    type: "bar",
    data: {
      labels: {{ labels_status | safe }},
      datasets: [{
        label: "Total por Status",
        data: {{ valores_status | safe }},
        backgroundColor: "#3498db"
      }]
    }
  });

  new Chart(document.getElementById("graficoCategoria"), {
    type: "doughnut",
    data: {
      labels: {{ labels_categoria | safe }},
      datasets: [{
        data: {{ valores_categoria | safe }},
        backgroundColor: ["#8e44ad", "#f39c12", "#27ae60", "#e74c3c", "#2c3e50"]
      }]
    },
    options: {
      plugins: {
        legend: { position: "bottom" }
      }
    }
  });

  new Chart(document.getElementById("graficoLinha"), {
    type: 'line',
    data: {
      labels: {{ dias_futuros | safe }},
      datasets: [{
        label: 'Contas a Pagar',
        data: {{ valores_futuros | safe }},
        borderColor: '#00009f',
        fill: false
      }]
    }
  });
</script>
{% endblock %}
