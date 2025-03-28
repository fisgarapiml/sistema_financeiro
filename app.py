from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

# ✅ Filtro para input type="date"
@app.template_filter("data_input")
def data_input_format(data_brasileira):
    try:
        return datetime.strptime(data_brasileira, "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return ""

# 📌 Conexão com o banco
def conectar():
    return sqlite3.connect("grupo_fisgar.db")

# ✅ Dashboard principal
@app.route("/dashboard")
def dashboard():
    conn = conectar()
    cursor = conn.cursor()

    # 📅 Filtro de período
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    hoje = datetime.today()
    if not data_inicio:
        data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
    if not data_fim:
        ultimo_dia = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        data_fim = ultimo_dia.strftime("%Y-%m-%d")

    # 📌 Ajuste para comparar datas armazenadas como dd/mm/yyyy
    query = """
        SELECT fornecedor, vencimento, valor, valor_pago, status, categorias
        FROM contas_a_pagar
        WHERE date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2))
        BETWEEN ? AND ?
    """
    cursor.execute(query, (data_inicio, data_fim))
    resultados = cursor.fetchall()

    # 💰 Cálculos corretos com conversão para float
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

    conn.close()

    return render_template("dashboard_financeiro.html",
        data_inicio=data_inicio,
        data_fim=data_fim,
        total_previsto=total_previsto,
        total_pago=total_pago,
        saldo=saldo,
        labels_status=labels_status,
        valores_status=valores_status,
        labels_categoria=labels_categoria,
        valores_categoria=valores_categoria
    )

# ✅ Rota: Contas a Pagar
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

# ✅ Rota: Editar Lançamento
@app.route("/editar/<int:codigo>", methods=["GET", "POST"])
def editar_lancamento(codigo):
    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        try:
            dados = {
                "fornecedor": request.form.get("fornecedor"),
                "categorias": request.form.get("categoria"),
                "tipo_custo": request.form.get("tipo"),
                "centro_de_custo": request.form.get("centro_de_custo"),
                "status": request.form.get("status"),
                "vencimento": request.form.get("vencimento"),
                "emissao": request.form.get("emissao"),
                "valor": request.form.get("valor"),
                "valor_pago": request.form.get("valor_pago"),
                "produtos": request.form.get("produtos"),
                "comentario": request.form.get("observacoes")
            }

            cursor.execute("""
                UPDATE contas_a_pagar SET
                    fornecedor = ?, categorias = ?, tipo_custo = ?, centro_de_custo = ?,
                    status = ?, vencimento = ?, emissao = ?, valor = ?, valor_pago = ?,
                    produtos = ?, comentario = ?
                WHERE codigo = ?
            """, (*dados.values(), codigo))
            conn.commit()
            mensagem = "✅ Lançamento atualizado com sucesso!"
        except Exception as e:
            mensagem = f"❌ Erro ao atualizar: {str(e)}"
        finally:
            conn.close()
        return f"{mensagem} <a href='/contas'>Voltar</a>"

    else:
        cursor.execute("SELECT * FROM contas_a_pagar WHERE codigo = ?", (codigo,))
        dados = cursor.fetchone()

        if not dados:
            conn.close()
            return "❌ Lançamento não encontrado. <a href='/contas'>Voltar</a>"

        cursor.execute("SELECT DISTINCT fornecedor FROM contas_a_pagar WHERE fornecedor IS NOT NULL")
        fornecedores = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT categorias FROM contas_a_pagar WHERE categorias IS NOT NULL")
        categorias = [row[0] for row in cursor.fetchall()]

        conn.close()
        return render_template("editar_lancamento.html", dados=dados, fornecedores=fornecedores, categorias=categorias)

# ✅ Edição em Massa
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

# ✅ Executar
if __name__ == "__main__":
    app.run(debug=True)
