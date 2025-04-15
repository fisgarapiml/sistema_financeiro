from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date
import sqlite3
import json
import os

app = Flask(__name__, template_folder='templates', static_folder='static')


# Funções auxiliares
def formatar_brl(valor):
    """Formata valores monetários no padrão brasileiro"""
    try:
        valor_float = float(valor) if valor is not None else 0.0
        return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"


def calcular_status(vencimento_str, valor_pago):
    """Calcula o status do lançamento baseado na data de vencimento e se foi pago"""
    if valor_pago and float(valor_pago) > 0:
        return 'paid'

    try:
        day, month, year = map(int, vencimento_str.split('/'))
        vencimento = date(year, month, day)
        hoje = date.today()

        if vencimento < hoje:
            return 'overdue'
        return 'pending'
    except:
        return 'pending'


def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados"""
    conn = sqlite3.connect("C:/sistema_financeiro/grupo_fisgar.db")
    conn.row_factory = sqlite3.Row  # Converte para dicionário
    return conn


# Rotas principais
@app.route("/")
def index():
    return redirect(url_for('contas_a_pagar'))


@app.route("/contas_a_pagar")
def contas_a_pagar():
    conn = get_db_connection()
    try:
        contas = conn.execute('''
            SELECT codigo, fornecedor, documento, vencimento, 
                   valor, valor_pago, categorias, plano_de_contas,
                   CASE 
                      WHEN date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now') 
                           AND (valor_pago IS NULL OR valor_pago = 0) THEN 'overdue'
                      WHEN valor_pago > 0 THEN 'paid'
                      ELSE 'pending'
                   END as status
            FROM contas_a_pagar
            ORDER BY vencimento
        ''').fetchall()

        fornecedores = [f[0] for f in conn.execute(
            'SELECT DISTINCT fornecedor FROM contas_a_pagar WHERE fornecedor IS NOT NULL').fetchall()]

        return render_template('contas_a_pagar.html',
                               contas=contas,
                               fornecedores=fornecedores,
                               formatar_brl=formatar_brl)
    except Exception as e:
        flash(f"Erro ao carregar contas: {str(e)}", "danger")
        return render_template('contas_a_pagar.html', contas=[], fornecedores=[], formatar_brl=formatar_brl)
    finally:
        conn.close()


@app.route("/indicadores")
def indicadores():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        hoje = datetime.today()
        mes_param = request.args.get("mes", hoje.month)
        ano_param = request.args.get("ano", hoje.year)
        filtro = request.args.get("filtro", "mes")

        mes_corrente = f"{int(mes_param):02d}/{ano_param}"

        cursor.execute("""
            SELECT 
                substr(vencimento, 1, 2) as dia,
                SUM(CAST(valor AS FLOAT)) as total,
                CASE 
                    WHEN date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now') 
                         AND (valor_pago IS NULL OR valor_pago = 0) THEN 'overdue'
                    WHEN valor_pago > 0 THEN 'paid'
                    ELSE 'pending'
                END as status
            FROM contas_a_pagar
            WHERE substr(vencimento, 4, 7) = ?
            GROUP BY dia, status
            ORDER BY dia
        """, (mes_corrente,))

        daily_data = {}
        for row in cursor.fetchall():
            dia, total, status = row
            total = abs(total) if total is not None else 0.0

            if dia in daily_data:
                daily_data[dia]['total'] += total
                if status == 'overdue' or (status == 'pending' and daily_data[dia]['status'] == 'paid'):
                    daily_data[dia]['status'] = status
            else:
                daily_data[dia] = {'total': total, 'status': status}

        days_in_month = 31
        complete_daily_data = {}
        for day in range(1, days_in_month + 1):
            day_str = f"{day:02d}"
            complete_daily_data[day_str] = daily_data.get(day_str, {'total': 0, 'status': 'none'})

        def get_sql_result(query, params=()):
            cursor.execute(query, params)
            result = cursor.fetchone()[0]
            return float(result) if result is not None else 0.0

        total_previsto = get_sql_result("""
            SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
            WHERE substr(vencimento, 4, 7) = ?
            """, (mes_corrente,))

        total_pago = get_sql_result("""
            SELECT SUM(CAST(valor_pago AS FLOAT)) FROM contas_a_pagar
            WHERE substr(vencimento, 4, 7) = ?
            """, (mes_corrente,))

        saldo = total_pago + total_previsto

        valor_vencido_total = get_sql_result("""
            SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
            AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now')
            """)

        valor_hoje_total = get_sql_result("""
            SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
            AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) = date('now')
            """)

        query_lancamentos = """
            SELECT codigo, vencimento, categorias, fornecedor, plano_de_contas, valor, valor_pago
            FROM contas_a_pagar
            WHERE 1=1
            """

        params = []

        if filtro == "atrasados":
            titulo_lancamentos = "Contas Vencidas"
            query_lancamentos += """
                AND (valor_pago IS NULL OR valor_pago = 0)
                AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now')
                """
        elif filtro == "hoje":
            titulo_lancamentos = "Contas a Pagar Hoje"
            query_lancamentos += """
                AND (valor_pago IS NULL OR valor_pago = 0)
                AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) = date('now')
                """
        else:
            titulo_lancamentos = f"Lançamentos de {mes_corrente}"
            query_lancamentos += " AND substr(vencimento, 4, 7) = ?"
            params.append(mes_corrente)

        query_lancamentos += " ORDER BY vencimento ASC"
        cursor.execute(query_lancamentos, params)

        lancamentos = []
        for row in cursor.fetchall():
            codigo, vencimento, categoria, fornecedor, plano, valor, valor_pago = row
            status = calcular_status(vencimento, valor_pago)
            lancamentos.append({
                "codigo": codigo,
                "vencimento": vencimento,
                "categoria": categoria or '-',
                "fornecedor": fornecedor or '-',
                "plano": plano or '-',
                "valor": float(valor) if valor is not None else 0.0,
                "pago": float(valor_pago) if valor_pago is not None else 0.0,
                "status": status
            })

        return render_template(
            "dashboard_contas_a_pagar.html",
            total_previsto=total_previsto,
            total_pago=total_pago,
            saldo=saldo,
            vencidas=valor_vencido_total,
            a_vencer=valor_hoje_total,
            lancamentos=lancamentos,
            titulo_lancamentos=titulo_lancamentos,
            formatar_brl=formatar_brl,
            daily_payments=json.dumps(complete_daily_data),
            current_month=int(mes_param),
            current_year=int(ano_param),
            mes_corrente=mes_corrente
        )

    except Exception as e:
        print(f"Erro: {str(e)}")
        return render_template("error.html", error=str(e))
    finally:
        conn.close()


@app.route("/lancamento_manual", methods=["GET", "POST"])
def lancamento_manual():
    conn = get_db_connection()

    if request.method == "POST":
        try:
            dados = {
                'fornecedor': request.form.get('fornecedor'),
                'categorias': request.form.get('categorias'),
                'plano_de_contas': request.form.get('plano_de_contas'),
                'valor': request.form.get('valor'),
                'vencimento': request.form.get('vencimento'),
                'valor_pago': request.form.get('valor_pago'),
                'centro_de_custo': request.form.get('centro_de_custo'),
                'empresa': request.form.get('empresa'),
                'conta': request.form.get('conta'),
                'tipo_custo': request.form.get('tipo_custo'),
                'tipo': request.form.get('tipo'),
                'status': request.form.get('status') or calcular_status(request.form.get('vencimento'),
                                                                        request.form.get('valor_pago')),
                'documento': request.form.get('documento'),
                'tipo_documento': request.form.get('tipo_documento'),
                'pagamento_tipo': request.form.get('pagamento_tipo'),
                'comentario': request.form.get('comentario'),
                'data_cadastro': datetime.now().strftime('%d/%m/%Y'),
                'data_competencia': request.form.get('data_competencia'),
                'data_documento': request.form.get('data_documento')
            }

            conn.execute("""
                INSERT INTO contas_a_pagar (
                    fornecedor, categorias, plano_de_contas, valor, vencimento,
                    valor_pago, centro_de_custo, empresa, conta, tipo_custo,
                    tipo, status, documento, tipo_documento, pagamento_tipo,
                    comentario, data_cadastro, data_competencia, data_documento
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(dados.values()))

            conn.commit()
            flash("Lançamento cadastrado com sucesso!", "success")
            return redirect(url_for('lancamento_manual'))

        except Exception as e:
            conn.rollback()
            flash(f"Erro ao cadastrar: {str(e)}", "danger")

    try:
        campos_select = {
            'fornecedores': conn.execute(
                "SELECT DISTINCT fornecedor FROM contas_a_pagar WHERE fornecedor IS NOT NULL").fetchall(),
            'categorias': conn.execute(
                "SELECT DISTINCT categorias FROM contas_a_pagar WHERE categorias IS NOT NULL").fetchall(),
            'planos': conn.execute(
                "SELECT DISTINCT plano_de_contas FROM contas_a_pagar WHERE plano_de_contas IS NOT NULL").fetchall(),
            'centros_custo': conn.execute(
                "SELECT DISTINCT centro_de_custo FROM contas_a_pagar WHERE centro_de_custo IS NOT NULL").fetchall(),
            'empresas': conn.execute(
                "SELECT DISTINCT empresa FROM contas_a_pagar WHERE empresa IS NOT NULL").fetchall(),
            'contas': conn.execute("SELECT DISTINCT conta FROM contas_a_pagar WHERE conta IS NOT NULL").fetchall(),
            'tipos_custo': conn.execute(
                "SELECT DISTINCT tipo_custo FROM contas_a_pagar WHERE tipo_custo IS NOT NULL").fetchall(),
            'tipos': conn.execute("SELECT DISTINCT tipo FROM contas_a_pagar WHERE tipo IS NOT NULL").fetchall(),
            'tipos_doc': conn.execute(
                "SELECT DISTINCT tipo_documento FROM contas_a_pagar WHERE tipo_documento IS NOT NULL").fetchall(),
            'formas_pagto': conn.execute(
                "SELECT DISTINCT pagamento_tipo FROM contas_a_pagar WHERE pagamento_tipo IS NOT NULL").fetchall()
        }

        opcoes = {k: [item[0] for item in v] for k, v in campos_select.items()}

        return render_template("lancamento_manual.html", **opcoes)

    except Exception as e:
        flash(f"Erro ao carregar opções: {str(e)}", "danger")
        return render_template("lancamento_manual.html")
    finally:
        conn.close()


@app.route("/marcar_pago", methods=["POST"])
def marcar_pago():
    try:
        codigo = request.args.get("codigo")
        if not codigo:
            return jsonify({"success": False, "error": "Código não fornecido"}), 400

        conn = get_db_connection()
        conn.execute("UPDATE contas_a_pagar SET valor_pago = valor, status = 'paid' WHERE codigo = ?", (codigo,))
        conn.commit()
        return jsonify({"success": True, "message": "Marcado como pago"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@app.route("/excluir", methods=["POST"])
def excluir():
    try:
        codigo = request.args.get("codigo")
        if not codigo:
            return jsonify({"success": False, "error": "Código não fornecido"}), 400

        conn = get_db_connection()
        conn.execute("DELETE FROM contas_a_pagar WHERE codigo = ?", (codigo,))
        conn.commit()
        return jsonify({"success": True, "message": "Registro excluído"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@app.route("/editar", methods=["POST"])
def editar():
    try:
        data = request.get_json()
        if not data or "codigo" not in data:
            return jsonify({"success": False, "error": "Dados inválidos"}), 400

        conn = get_db_connection()
        conn.execute("""
            UPDATE contas_a_pagar
            SET fornecedor = ?, categorias = ?, plano_de_contas = ?, vencimento = ?, valor = ?
            WHERE codigo = ?
        """, (
            data.get("fornecedor"),
            data.get("categoria"),
            data.get("plano"),
            data.get("vencimento"),
            data.get("valor"),
            data.get("codigo")
        ))
        conn.commit()
        return jsonify({"success": True, "message": "Registro atualizado"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@app.route('/editar_massa', methods=['POST'])
def editar_massa():
    try:
        data = request.get_json()
        if not data or 'ids' not in data:
            return jsonify({"success": False, "error": "Dados inválidos"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if 'status' in data:
            updates.append("status = ?")
            params.append(data['status'])

        if 'vencimento' in data:
            updates.append("vencimento = ?")
            params.append(data['vencimento'])

        if 'fornecedor' in data:
            updates.append("fornecedor = ?")
            params.append(data['fornecedor'])

        if updates:
            query = "UPDATE contas_a_pagar SET " + ", ".join(updates) + " WHERE codigo IN (" + ",".join(
                ["?"] * len(data['ids'])) + ")"
            params.extend(data['ids'])
            cursor.execute(query, params)
            conn.commit()

        return jsonify({"success": True, "message": "Atualizado com sucesso"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@app.route('/estoque')
def estoque():
    conn = get_db_connection()
    try:
        # Dados para os cards
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_itens,
                SUM(CASE WHEN estoque_atual > estoque_minimo THEN 1 ELSE 0 END) as itens_ok,
                SUM(CASE WHEN estoque_atual > 0 AND estoque_atual <= estoque_minimo THEN 1 ELSE 0 END) as itens_baixos,
                SUM(CASE WHEN estoque_atual = 0 THEN 1 ELSE 0 END) as itens_esgotados
            FROM produtos
        ''')
        cards_data = cursor.fetchone()

        # Itens críticos
        cursor.execute('''
            SELECT p.codigo, p.nome, p.categoria, f.nome as fornecedor, 
                   p.estoque_atual, p.estoque_minimo,
                   CASE 
                       WHEN p.estoque_atual = 0 THEN 'Esgotado'
                       WHEN p.estoque_atual <= p.estoque_minimo THEN 'Crítico'
                       ELSE 'OK'
                   END as status,
                   (SELECT MAX(data) FROM movimentacoes WHERE produto_id = p.id AND tipo = 'entrada') as ultima_entrada
            FROM produtos p
            LEFT JOIN fornecedores f ON p.fornecedor_id = f.id
            WHERE p.estoque_atual <= p.estoque_minimo
            ORDER BY p.estoque_atual ASC
            LIMIT 50
        ''')
        itens_criticos = [dict(row) for row in cursor.fetchall()]

        # Dados para gráficos (simplificado)
        meses = ['Jan', 'Fev', 'Mar']
        entradas = [120, 190, 170]
        saidas = [80, 120, 140]
        categorias = ['Eletrônicos', 'Materiais']
        valores = [12000, 5000]

        return render_template('estoque.html',
                               cards_data=cards_data,
                               itens_criticos=itens_criticos,
                               meses=json.dumps(meses),
                               entradas=json.dumps(entradas),
                               saidas=json.dumps(saidas),
                               categorias=json.dumps(categorias),
                               valores=json.dumps(valores))

    except Exception as e:
        print(f"Erro na rota estoque: {str(e)}")
        # Dados de fallback caso ocorra erro
        dados_fallback = {
            'cards_data': {
                'total_itens': 0,
                'itens_ok': 0,
                'itens_baixos': 0,
                'itens_esgotados': 0
            },
            'itens_criticos': [],
            'meses': json.dumps([]),
            'entradas': json.dumps([]),
            'saidas': json.dumps([]),
            'categorias': json.dumps([]),
            'valores': json.dumps([])
        }
        return render_template('estoque.html', **dados_fallback)
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)