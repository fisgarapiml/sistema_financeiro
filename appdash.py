from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

# ✅ Conexão com banco de dados
def conectar():
    return sqlite3.connect("grupo_fisgar.db")

# ✅ Dashboard
@app.route("/dashboard")
def dashboard():
    conn = conectar()
    cursor = conn.cursor()

    # 📅 Período
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    hoje = datetime.today()
    if not data_inicio:
        data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
    if not data_fim:
        ultimo_dia = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        data_fim = ultimo_dia.strftime("%Y-%m-%d")

    # ✅ Buscar dados do período
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

    # ✅ Contas vencem hoje
    hoje_str = hoje.strftime("%d/%m/%Y")
    cursor.execute("""
        SELECT fornecedor, categorias, valor FROM contas_a_pagar
        WHERE vencimento = ? AND status != 'Pago'
    """, (hoje_str,))
    contas_hoje = cursor.fetchall()
    total_hoje = sum([float(r[2]) for r in contas_hoje])

    # ✅ Contas em atraso
    cursor.execute("""
        SELECT fornecedor, categorias, valor FROM contas_a_pagar
        WHERE date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now')
        AND status != 'Pago'
    """)
    contas_atraso = cursor.fetchall()
    total_atraso = sum([float(r[2]) for r in contas_atraso])

    # ✅ Necessidade de caixa amanhã
    amanha = (hoje + timedelta(days=1)).strftime("%d/%m/%Y")
    cursor.execute("""
        SELECT valor FROM contas_a_pagar
        WHERE vencimento = ? AND status != 'Pago'
    """, (amanha,))
    total_amanha = sum([float(r[0]) for r in cursor.fetchall()])
    necessidade_caixa = total_amanha - 0  # futuro: subtrair entradas previstas

    # ✅ Gráfico por status
    resumo_status = {}
    for r in resultados:
        status = r[4] or "Não Informado"
        resumo_status[status] = resumo_status.get(status, 0) + float(r[2])
    labels_status = list(resumo_status.keys())
    valores_status = list(resumo_status.values())

    # ✅ Gráfico por categoria
    resumo_categoria = {}
    for r in resultados:
        cat = r[5] or "Não Informada"
        resumo_categoria[cat] = resumo_categoria.get(cat, 0) + float(r[2])
    labels_categoria = list(resumo_categoria.keys())
    valores_categoria = list(resumo_categoria.values())

    # ✅ Gráfico de linha - próximos 7 dias
    dias_futuros = []
    valores_futuros = []
    for i in range(7):
        dia = (hoje + timedelta(days=i)).strftime("%d/%m/%Y")
        cursor.execute("""
            SELECT valor FROM contas_a_pagar
            WHERE vencimento = ? AND status != 'Pago'
        """, (dia,))
        soma = sum([float(r[0]) for r in cursor.fetchall()])
        dias_futuros.append(dia)
        valores_futuros.append(soma)

    conn.close()

    return render_template("dashboard_financeiro.html",
        data_inicio=data_inicio,
        data_fim=data_fim,
        total_previsto=total_previsto,
        total_pago=total_pago,
        saldo=saldo,
        total_hoje=total_hoje,
        contas_hoje=contas_hoje,
        total_atraso=total_atraso,
        contas_atraso=contas_atraso,
        necessidade_caixa=necessidade_caixa,
        labels_status=labels_status,
        valores_status=valores_status,
        labels_categoria=labels_categoria,
        valores_categoria=valores_categoria,
        dias_futuros=dias_futuros,
        valores_futuros=valores_futuros
    )

# ✅ Página Contas a Pagar
@app.route("/contas")
def contas():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fornecedor, vencimento, valor, valor_pago, (valor + valor_pago) as pendente,
               status, categorias, tipo_custo, centro_de_custo, codigo
        FROM contas_a_pagar
        ORDER BY vencimento ASC
    """)
    dados = cursor.fetchall()
    conn.close()
    return render_template("contas_a_pagar.html", dados=dados)

# ✅ Página de Edição em Massa
@app.route("/editar_em_massa", methods=["GET", "POST"])
def editar_em_massa():
    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        cursor.execute("SELECT codigo FROM contas_a_pagar")
        codigos = [row[0] for row in cursor.fetchall()]
        for codigo in codigos:
            fornecedor = request.form.get(f"fornecedor_{codigo}")
            categoria = request.form.get(f"categoria_{codigo}")
            status = request.form.get(f"status_{codigo}")
            vencimento = request.form.get(f"vencimento_{codigo}")
            valor = request.form.get(f"valor_{codigo}")
            valor_pago = request.form.get(f"valor_pago_{codigo}")
            if fornecedor:
                cursor.execute("""
                    UPDATE contas_a_pagar
                    SET fornecedor=?, categorias=?, status=?, vencimento=?, valor=?, valor_pago=?
                    WHERE codigo=?
                """, (fornecedor, categoria, status, vencimento, valor, valor_pago, codigo))
        conn.commit()
        conn.close()
        return redirect("/contas")

    cursor.execute("""
        SELECT codigo, fornecedor, categorias, status, vencimento, valor, valor_pago
        FROM contas_a_pagar
        ORDER BY vencimento
    """)
    dados = cursor.fetchall()

    cursor.execute("SELECT DISTINCT fornecedor FROM contas_a_pagar WHERE fornecedor IS NOT NULL AND fornecedor != ''")
    fornecedores = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT categorias FROM contas_a_pagar WHERE categorias IS NOT NULL AND categorias != ''")
    categorias = [row[0] for row in cursor.fetchall()]

    conn.close()
    return render_template("editar_em_massa.html", dados=dados, fornecedores=fornecedores, categorias=categorias)

# ✅ Página inicial
@app.route("/")
def index():
    return redirect("/dashboard")

# ✅ Roda o servidor
if __name__ == "__main__":
    app.run(debug=True)
