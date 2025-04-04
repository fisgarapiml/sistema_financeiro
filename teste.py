{% extends "base.html" %}

{% block conteudo %}
<!-- 🌌 ESTILO GALÁXIA -->
<style>
  .grafico-galaxia-categorias {
    background-image: url('/static/images/galaxia5.png');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    border-radius: 24px;
    padding: 40px 30px;
    margin-top: 40px;
    box-shadow: 0 0 25px rgba(0,0,0,0.3);
    color: white;
  }
</style>

<div class="container mt-4" style="font-family: 'Poppins', sans-serif;">

  <!-- 🔷 Título e Filtro -->
  <div class="d-flex justify-content-between align-items-start mb-4 flex-wrap gap-3">
    <h3 class="mb-0">📋 Contas a Pagar</h3>
    <form method="GET" class="d-flex gap-2 flex-wrap align-items-end">
      <div class="border border-primary border-2 rounded-3 px-3 py-2 shadow-sm">
        <label class="form-label text-muted small mb-1">De</label>
        <input type="date" name="data_de" value="{{ data_de }}" class="form-control form-control-sm border-0">
      </div>
      <div class="border border-primary border-2 rounded-3 px-3 py-2 shadow-sm">
        <label class="form-label text-muted small mb-1">Até</label>
        <input type="date" name="data_ate" value="{{ data_ate }}" class="form-control form-control-sm border-0">
      </div>
      <button type="submit" class="btn btn-primary px-4 shadow-sm">Filtrar</button>
    </form>
  </div>
< !-- 📊 Cards
Totais -->
< div


class ="row g-3 mb-4" >


{ %
for c in cards %}
< div


class ="col-md-2 col-sm-4 col-6" >

< div


class ="card border border-primary border-2 rounded-4 shadow-sm overflow-hidden" >

< !-- Faixa
Azul
com
Título -->
< div


class ="bg-primary text-white py-1 px-2 text-center" style="font-size: 0.8rem; font-weight: 500;" >


{{c.titulo}}
< / div >
< !-- Valor
Centralizado -->
< div


class ="card-body d-flex align-items-center justify-content-center fs-5" >


{ % if c.titulo == 'Amanhã' %}
{ % if c.valor | float > 0 %}
< span


class ="text-danger" > R$ {{"%.2f" | format(c.valor | float)}} < / span >


{ % else %}
< span


class ="text-success" > ✅ < / span >


{ % endif %}
{ % else %}
< span


class ="{{ c.classe if c.classe is defined else (


'text-danger' if c.valor | float < 0 else 'text-success' if c.valor | float > 0 else 'text-muted'
)}}">{{ c.valor }}</span>
{ % endif %}
< / div >
    < / div >
        < / div >
            { % endfor %}
< / div >
<!-- 🌌 Gráfico Galáxia + Lançamentos do Dia -->
<div class="row g-3 mt-3">
  <!-- Gráfico Galáctico de Categorias -->
  <div class="col-md-6">
    <div class="grafico-galaxia-categorias">
      <div id="grafico_categoria"></div>
    </div>
  </div>

  <!-- Lançamentos do Dia -->
  <div class="col-md-6">
    <div class="card shadow-sm rounded-4 p-3">
      <h5 class="mb-3">📅 Lançamentos de Hoje</h5>
      <div id="lancamentosHoje" style="display: flex; flex-direction: column; gap: 14px;"></div>
    </div>
  </div>
</div>
<!-- 🚀 MODAL DETALHES POR CATEGORIA -->
<div id="modalCategoria" style="
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.85);
  z-index: 9999;
  overflow-y: auto;
  padding: 40px;
  font-family: 'Segoe UI', sans-serif;
">
  <div style="
    background: #0f172a;
    border-radius: 24px;
    padding: 30px;
    color: white;
    max-width: 900px;
    margin: 0 auto;
    box-shadow: 0 0 25px rgba(0,0,0,0.6);
    position: relative;
  ">
    <div style="text-align: right; margin-bottom: 15px;">
      <button onclick="fecharModalCategoria()" style="
        background: #0d6efd;
        border: none;
        padding: 10px 20px;
        color: white;
        font-weight: 600;
        border-radius: 10px;
        cursor: pointer;
      ">Fechar</button>
    </div>
    <div id="modalConteudo"></div>
  </div>
</div>
<!-- 📊 INTERAÇÃO COM O GRÁFICO DE CATEGORIAS -->
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<script>
  // 🔁 Renderiza o gráfico
  Plotly.newPlot('grafico_categoria', {{ grafico_categoria | safe }}, {responsive: true});

  // 🌠 Clicar em uma bolha = abrir o modal com os lançamentos
  document.addEventListener("DOMContentLoaded", function () {
    const grafico = document.getElementById('grafico_categoria');
    if (grafico && grafico.__plotly__) {
      grafico.on('plotly_click', function (data) {
        const categoria = data.points[0].customdata;
        abrirModalCategoria(categoria);
      });
    }
  });

  // 🚪 Abre o modal
  function abrirModalCategoria(categoria) {
    fetch(`/detalhes-categoria?categoria=${encodeURIComponent(categoria)}`)
      .then(response => response.text())
      .then(html => {
        document.getElementById("modalConteudo").innerHTML = html;
        document.getElementById("modalCategoria").style.display = "block";
      });
  }

  // ❌ Fecha o modal e reseta as bolhas
  function fecharModalCategoria() {
    document.getElementById("modalCategoria").style.display = "none";
    Plotly.restyle("grafico_categoria", { 'selectedpoints': [null] });
  }
</script>
<script>
  const hoje = new Date().toLocaleDateString("pt-BR");
  const lancamentos = {{ lancamentos_categoria | tojson }};
  const container = document.getElementById("lancamentosHoje");

  Object.keys(lancamentos).forEach(categoria => {
    lancamentos[categoria].forEach(item => {
      if (item.vencimento === hoje) {
        const card = document.createElement("div");
        card.style.padding = "16px";
        card.style.borderRadius = "14px";
        card.style.background = "#f8f9fa";
        card.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.07)";
        card.style.borderLeft = item.status === 'Pago' ? "5px solid green" : "5px solid red";

        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div style="flex: 1;">
              <div style="font-weight: 600; font-size: 16px;">${item.fornecedor}</div>
              <div style="font-size: 13px; color: #777;">📂 ${categoria}</div>
              <div style="font-size: 13px; color: #777;">🏷️ ${item.tipo} | 🏢 ${item.centro}</div>
              <div style="margin-top: 6px;" id="status-${item.codigo}">
                ${
                  item.status === 'Pago'
                    ? '<span style="color: green; font-weight: 500;">✔️ Pago</span>'
                    : `<span style="color: red; font-weight: 500;">🔴 Pendente</span>
                       <button onclick="baixarLancamento('${item.codigo}')" style="
                         margin-top: 6px;
                         background-color: #0d6efd;
                         border: none;
                         color: white;
                         font-size: 12px;
                         padding: 4px 10px;
                         border-radius: 20px;
                         cursor: pointer;
                         display: inline-block;
                       ">💸 Dar Baixa</button>`
                }
              </div>
            </div>
            <div style="text-align: right; font-size: 18px; font-weight: bold; color: #2b2b2b;">
              💰 R$ ${item.valor}
            </div>
          </div>
        `;

        container.appendChild(card);
      }
    });
  });

  // Função para dar baixa diretamente
  function baixarLancamento(codigo) {
    fetch(`/baixar-lancamento/${codigo}`, { method: 'POST' })
      .then(response => {
        if (response.ok) {
          const div = document.getElementById('status-' + codigo);
          div.innerHTML = '<span style="color: green; font-weight: 500;">✔️ Pago</span>';
        } else {
          alert("Erro ao dar baixa.");
        }
      });
  }
</script>




