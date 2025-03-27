from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

def formatar(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

@app.route("/", methods=["GET", "POST"])
def index():
    conn = sqlite3.connect("grupo_fisgar.db")
    cursor = conn.cursor()

    # Buscar opções únicas
    status_opcoes = [row[0] for row in cursor.execute("SELECT DISTINCT status FROM contas_a_pagar")]
    categoria_opcoes = [row[0] for row in cursor.execute("SELECT DISTINCT categorias FROM contas_a_pagar")]
    fornecedor_opcoes = [row[0] for row in cursor.execute("SELECT DISTINCT fornecedor FROM contas_a_pagar")]

    status = request.form.get("status", "")
    categoria = request.form.get("categoria", "")
    fornecedor = request.form.get("fornecedor", "")

    query = "SELECT valor FROM contas_a_pagar WHERE 1=1"
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
    valores = cursor.fetchall()
    total = sum(float(str(v[0]).replace(",", ".")) for v in valores)

    conn.close()

    return render_template("index.html",
                           total=total,
                           status_opcoes=status_opcoes,
                           categoria_opcoes=categoria_opcoes,
                           fornecedor_opcoes=fornecedor_opcoes,
                           status_atual=status,
                           categoria_atual=categoria,
                           fornecedor_atual=fornecedor)

if __name__ == "__main__":
    app.run(debug=True)
