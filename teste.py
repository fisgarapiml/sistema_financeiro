from flask import Flask, jsonify, render_template, request
import sqlite3

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect("C:/sistema_financeiro/grupo_fisgar.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    conn = get_db()
    try:
        contas = conn.execute("""
            SELECT 
                codigo, 
                fornecedor, 
                vencimento, 
                CAST(valor AS REAL) as valor,
                CASE 
                    WHEN status = 'pago' THEN 'pago'
                    WHEN date(vencimento) < date('now') THEN 'atrasado'
                    ELSE 'pendente'
                END as status
            FROM contas_a_pagar 
            LIMIT 50
        """).fetchall()
        return render_template("contas.html", contas=contas)
    except Exception as e:
        return f"Erro ao acessar o banco de dados: {str(e)}", 500
    finally:
        conn.close()


@app.route("/editar_massa", methods=["POST"])
def editar_massa():
    try:
        data = request.get_json()
        if not data or 'ids' not in data:
            return jsonify({"success": False, "error": "Dados inválidos"}), 400

        conn = get_db()
        cursor = conn.cursor()

        updates = []
        params = []

        if data.get('status'):
            updates.append("status = ?")
            params.append(data['status'])

        if data.get('fornecedor'):
            updates.append("fornecedor = ?")
            params.append(data['fornecedor'])

        if not updates:
            return jsonify({"success": False, "error": "Nenhum campo para atualizar"}), 400

        placeholders = ','.join(['?'] * len(data['ids']))
        query = f"UPDATE contas_a_pagar SET {', '.join(updates)} WHERE codigo IN ({placeholders})"
        params.extend(data['ids'])

        cursor.execute(query, params)
        conn.commit()
        return jsonify({"success": True, "updated": cursor.rowcount})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)