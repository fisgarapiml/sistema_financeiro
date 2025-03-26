from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ✅ Caminho fixo para o banco correto
DB_PATH = r"C:\Sistema Grupo Fisgar\grupo_fisgar.db"

def conectar():
    return sqlite3.connect(DB_PATH)

# ✅ Formatador de valores
def formatar(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# ✅ Página principal (filtros + listagem)
@app.route("/", methods=["GET"])
def index():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT status FROM contas_a_pagar WHERE status IS NOT NULL")
    status_opcoes = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT categorias FROM contas_a_pagar WHERE categorias IS NOT NULL")
    categorias_opcoes = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT fornecedor FROM contas_a_pagar WHERE fornecedor IS NOT NULL")
    fornecedores_opcoes = [row[0] for row in cursor.fetchall()]

    status = request.args.get("status", "")
    categoria = request.args.get("categoria", "")
    fornecedor = request.args.get("fornecedor", "")

    query = """
        SELECT codigo, fornecedor, vencimento, valor, valor_pago,
               ROUND(CAST(valor - valor_pago AS FLOAT), 2) AS pendente,
               status, categorias, tipo, centro_de_custo
        FROM contas_a_pagar
        WHERE 1=1
    """

    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if categoria:
        query += " AND categorias = ?"
        params.append(categoria)
    if fornecedor:
        query += " AND fornecedor = ?"
        params.append(fornecedor)

    cursor.execute(query, params)
    dados = cursor.fetchall()

    total_query = "SELECT valor FROM contas_a_pagar WHERE 1=1"
    total_params = []

    if status:
        total_query += " AND status = ?"
        total_params.append(status)
    if categoria:
        total_query += " AND categorias = ?"
        total_params.append(categoria)
    if fornecedor:
        total_query += " AND fornecedor = ?"
        total_params.append(fornecedor)

    cursor.execute(total_query, total_params)
    valores = cursor.fetchall()
    total = sum(float(str(v[0]).replace(",", ".")) for v in valores)

    conn.close()
    return render_template("contas_a_pagar.html",
                           dados=dados,
                           total=total,
                           status_opcoes=status_opcoes,
                           categorias_opcoes=categorias_opcoes,
                           fornecedores_opcoes=fornecedores_opcoes,
                           status_atual=status,
                           categoria_atual=categoria,
                           fornecedor_atual=fornecedor,
                           formatar=formatar)

# ✅ Página de novo lançamento
@app.route("/novo", methods=["GET", "POST"])
def novo_lancamento():
    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        dados = request.form

        cursor.execute("""
            INSERT INTO contas_a_pagar (
                fornecedor, categorias, tipo_custo, centro_de_custo, status,
                vencimento, emissao, valor, valor_pago, comentario,
                plano_de_contas, documento, documento_tipo, pagamento_tipo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dados.get("fornecedor"),
            dados.get("categoria"),
            dados.get("tipo"),
            dados.get("centro_de_custo"),
            dados.get("status"),
            dados.get("vencimento"),
            dados.get("emissao"),
            dados.get("valor"),
            dados.get("valor_pago"),
            dados.get("observacoes"),
            dados.get("plano_de_contas"),
            dados.get("documento"),
            dados.get("documento_tipo"),
            dados.get("pagamento_tipo")
        ))

        conn.commit()
        conn.close()
        return redirect("/")

    cursor.execute("SELECT DISTINCT fornecedor FROM contas_a_pagar WHERE fornecedor IS NOT NULL")
    fornecedores = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT categorias FROM contas_a_pagar WHERE categorias IS NOT NULL")
    categorias = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT plano_de_contas FROM contas_a_pagar WHERE plano_de_contas IS NOT NULL")
    planos = [row[0] for row in cursor.fetchall()]

    conn.close()
    return render_template("novo_lancamento.html",
                           fornecedores=fornecedores,
                           categorias=categorias,
                           planos=planos)

# ✅ Rota: Editar Lançamento (GET + POST)
@app.route("/editar/<int:codigo>", methods=["GET", "POST"])
def editar_lancamento(codigo):
    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        try:
            # Coleta os dados atualizados do formulário
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

            # Atualiza no banco
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

        return f"{mensagem} <a href='/'>Voltar</a>"

    # Se GET: buscar os dados do lançamento
    cursor.execute("SELECT * FROM contas_a_pagar WHERE codigo = ?", (codigo,))
    dados = cursor.fetchone()

    if not dados:
        conn.close()
        return "❌ Lançamento não encontrado. <a href='/'>Voltar</a>"

    # Carrega opções dos selects
    cursor.execute("SELECT DISTINCT fornecedor FROM contas_a_pagar WHERE fornecedor IS NOT NULL")
    fornecedores = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT categorias FROM contas_a_pagar WHERE categorias IS NOT NULL")
    categorias = [row[0] for row in cursor.fetchall()]

    conn.close()

    return render_template(
        "editar_lancamento.html",
        dados=dados,
        fornecedores=fornecedores,
        categorias=categorias
    )


# ✅ Executar servidor
if __name__ == "__main__":
    app.run(debug=True)
