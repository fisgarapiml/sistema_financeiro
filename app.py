from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime, timedelta
from contas_a_pagar import contas_a_pagar

app = Flask(__name__)

def conectar():
    return sqlite3.connect("grupo_fisgar.db")

@app.route("/")
def index():
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    conn = conectar()
    cursor = conn.cursor()

    # 📅 Período do filtro
    hoje = datetime.today()
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    if not data_inicio:
        data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
    if not data_fim:
        ultimo_dia = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        data_fim = ultimo_dia.strftime("%Y-%m-%d")

    # 📌 Consulta principal
    query = """
        SELECT fornecedor, vencimento, valor, valor_pago, status, categorias
        FROM contas_a_pagar
        WHERE date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2))
        BETWEEN ? AND ?
    """
    cursor.execute(query, (data_inicio, data_fim))
    resultados = cursor.fetchall()

    total_previsto = sum([float(r[2]) for r in resultados if r[2]])
    total_pago = sum([float(r[3]) for r in resultados if r[3]])
    saldo = total_pago + total_previsto

    # 📊 Resumo por Status
    resumo_status = {}
    for r in resultados:
        status = r[4] or "Não Informado"
        resumo_status[status] = resumo_status.get(status, 0) + float(r[2])
    labels_status = list(resumo_status.keys())
    valores_status = list(resumo_status.values())

    # 📊 Resumo por Categoria
    resumo_categoria = {}
    for r in resultados:
        categoria = r[5] or "Não Informada"
        resumo_categoria[categoria] = resumo_categoria.get(categoria, 0) + float(r[2])
    labels_categoria = list(resumo_categoria.keys())
    valores_categoria = list(resumo_categoria.values())

    # 📆 Contas com vencimento HOJE
    hoje_str = hoje.strftime("%d/%m/%Y")
    cursor.execute("""
        SELECT fornecedor, categorias, valor
        FROM contas_a_pagar
        WHERE vencimento = ? AND status != 'Pago'
    """, (hoje_str,))
    contas_hoje = cursor.fetchall()
    total_hoje = sum([float(r[2]) for r in contas_hoje if r[2]])

    # ❌ Contas em Atraso
    hoje_sql = hoje.strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT fornecedor, categorias, valor
        FROM contas_a_pagar
        WHERE 
          date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < ?
          AND status != 'Pago'
    """, (hoje_sql,))
    contas_atraso = cursor.fetchall()
    total_atraso = sum([float(r[2]) for r in contas_atraso if r[2]])

    # 📊 Previsão de Contas a Pagar (Gráfico de Linha)
    dias_futuros_labels = []
    dias_futuros_valores = []
    for i in range(1, 8):
        dia = hoje + timedelta(days=i)
        dia_str = dia.strftime("%d/%m/%Y")
        dia_label = dia.strftime("%d/%m")

        cursor.execute("""
            SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
            WHERE vencimento = ? AND status != 'Pago'
        """, (dia_str,))
        total_dia = cursor.fetchone()[0] or 0

        dias_futuros_labels.append(dia_label)
        dias_futuros_valores.append(round(total_dia, 2))

    # 📌 Simulação de Caixa do Amanhã
    cursor.execute("""
        SELECT SUM(CAST(valor_pago AS FLOAT)) FROM contas_a_pagar
        WHERE vencimento = ? AND status = 'Pago'
    """, (hoje_str,))
    caixa_hoje = cursor.fetchone()[0] or 0

    caixa_amanha = caixa_hoje  # Simulação: tudo o que caiu hoje, estará disponível amanhã
    contas_amanha_data = (hoje + timedelta(days=1)).strftime("%d/%m/%Y")
    cursor.execute("""
        SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
        WHERE vencimento = ? AND status != 'Pago'
    """, (contas_amanha_data,))
    apagar_amanha = cursor.fetchone()[0] or 0

    necessidade_caixa = apagar_amanha - caixa_amanha if apagar_amanha > caixa_amanha else 0

    conn.close()

    return render_template("dashboard_financeiro.html",
        data_inicio=data_inicio,
        data_fim=data_fim,
        total_previsto=total_previsto,
        total_pago=total_pago,
        saldo=saldo,
        total_hoje=total_hoje,
        total_atraso=total_atraso,
        contas_hoje=contas_hoje,
        contas_atraso=contas_atraso,
        necessidade_caixa=necessidade_caixa,
        labels_status=labels_status,
        valores_status=valores_status,
        labels_categoria=labels_categoria,
        valores_categoria=valores_categoria,
        dias_futuros_labels=dias_futuros_labels,
        dias_futuros_valores=dias_futuros_valores

    )
@app.route("/contas-a-pagar")
def rota_contas_a_pagar():
    return contas_a_pagar()
@app.route("/baixar-lancamento/<codigo>", methods=["POST"])
def baixar_lancamento(codigo):
    conexao = sqlite3.connect('grupo_fisgar.db')
    cursor = conexao.cursor()

    hoje = datetime.now().strftime("%d/%m/%Y")
    cursor.execute("""
        UPDATE contas_a_pagar
        SET status = 'Pago',
            valor_pago = valor
        WHERE codigo = ?
    """, (codigo,))
    conexao.commit()
    conexao.close()
    return '', 200


@app.route("/detalhes-categoria")
def detalhes_categoria():
    categoria = request.args.get("categoria")

    conexao = sqlite3.connect("grupo_fisgar.db")
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT fornecedor, vencimento, valor, valor_pago, status, tipo, centro_de_custo, codigo
        FROM contas_a_pagar
        WHERE categorias = ?
    """, (categoria,))
    resultados = cursor.fetchall()
    conexao.close()

    html = f"<h4 style='margin-bottom: 20px; color: #00ffff;'>🪐 Categoria: {categoria}</h4>"

    if not resultados:
        html += "<p>Nenhum lançamento encontrado.</p>"
    else:
        for r in resultados:
            status = r[4]
            cor_status = "#6c757d"  # cinza padrão
            cor_valor = "#ffffff"   # branco padrão

            if status.lower() == "pago":
                cor_status = "#00ff7f"  # verde
                cor_valor = "#00ff7f"
            elif status.lower() == "pendente":
                cor_status = "#ff9800"  # laranja
                cor_valor = "#ff9800"
            elif status.lower() == "atrasado":
                cor_status = "#ff3b3b"  # vermelho
                cor_valor = "#ff3b3b"

            html += f"""
            <div style="
                background: rgba(255,255,255,0.05);
                padding: 15px 20px 20px 20px;
                margin-bottom: 14px;
                border-radius: 14px;
                box-shadow: 0 0 18px rgba(0,0,0,0.3);
                border-left: 8px solid {cor_status};
                position: relative;
            ">

              <!-- Botão Editar flutuante -->
              <a href="/editar/{r[7]}" style="
                  position: absolute;
                  top: 15px;
                  right: 20px;
                  background: {cor_status};
                  color: black;
                  padding: 6px 12px;
                  border-radius: 8px;
                  font-weight: bold;
                  text-decoration: none;
                  font-size: 13px;
                  box-shadow: 0 0 6px rgba(0,0,0,0.4);
              ">✏️ Editar</a>

              <strong>Fornecedor:</strong> {r[0]}<br>
              <strong>Vencimento:</strong> {r[1]}<br>
              <strong>Valor:</strong> <span style="color: {cor_valor};">R$ {float(r[2]):,.2f}</span><br>
              <strong>Pago:</strong> <span style="color: {cor_valor};">R$ {float(r[3]):,.2f}</span><br>
              <strong>Status:</strong> {r[4]}<br>
              <strong>Tipo:</strong> {r[5]}<br>
              <strong>Centro de Custo:</strong> {r[6]}
            </div>
            """

    return html


@app.route("/editar/<codigo>")
def editar_lancamento(codigo):
    conexao = sqlite3.connect("grupo_fisgar.db")
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT fornecedor, vencimento, valor, valor_pago, status, categorias, tipo, centro_de_custo
        FROM contas_a_pagar
        WHERE codigo = ?
    """, (codigo,))
    dados = cursor.fetchone()
    conexao.close()

    if not dados:
        return f"<h3 style='color: red;'>Lançamento com código {codigo} não encontrado.</h3>"

    return render_template("editar_lancamento.html", codigo=codigo, dados=dados)
@app.route("/salvar-edicao/<codigo>", methods=["POST"])
def salvar_edicao(codigo):
    dados = (
        request.form["fornecedor"],
        request.form["vencimento"],
        request.form["valor"],
        request.form["valor_pago"],
        request.form["status"],
        request.form["categorias"],
        request.form["tipo"],
        request.form["centro_de_custo"],
        codigo
    )

    conexao = sqlite3.connect("grupo_fisgar.db")
    cursor = conexao.cursor()
    cursor.execute("""
        UPDATE contas_a_pagar
        SET fornecedor = ?, vencimento = ?, valor = ?, valor_pago = ?, status = ?,
            categorias = ?, tipo = ?, centro_de_custo = ?
        WHERE codigo = ?
    """, dados)
    conexao.commit()
    conexao.close()

    return redirect("/contas-a-pagar")




# 🚀 Executar o servidor
if __name__ == "__main__":
    app.run(debug=True)
