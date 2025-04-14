from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date
import sqlite3
import os

app = Flask(__name__)

# Funções auxiliares (consistentes com a rota /indicadores)
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

# Conexão com o banco (igual à rota /indicadores)
def get_db_connection():
    conn = sqlite3.connect("C:/sistema_financeiro/grupo_fisgar.db")
    conn.row_factory = sqlite3.Row  # Converte para dicionário
    return conn


@app.route("/indicadores")
def indicadores():
    try:
        conn = sqlite3.connect("C:/sistema_financeiro/grupo_fisgar.db")
        cursor = conn.cursor()
        conn = sqlite3.connect('grupo_fisgar.db')
        conn.row_factory = sqlite3.Row  # ← ESSENCIAL: isso transforma o resultado em dicionário
        cursor = conn.cursor()

        hoje = datetime.today()
        mes_param = request.args.get("mes", hoje.month)
        ano_param = request.args.get("ano", hoje.year)
        filtro = request.args.get("filtro", "mes")

        # Garante que mes/ano são strings com 2 dígitos
        mes_corrente = f"{int(mes_param):02d}/{ano_param}"

        # Consulta para obter os dias do mês com pagamentos
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

        # Processa os resultados para o formato diário
        daily_data = {}
        for row in cursor.fetchall():
            dia, total, status = row
            total = abs(total) if total is not None else 0.0  # ← Corrige valores negativos para exibição

            if dia in daily_data:
                daily_data[dia]['total'] += total
                # Mantém o status mais crítico (overdue > pending > paid)
                if status == 'overdue' or (status == 'pending' and daily_data[dia]['status'] == 'paid'):
                    daily_data[dia]['status'] = status
            else:
                daily_data[dia] = {'total': total, 'status': status}

        # Preenche os dias sem lançamentos com zero
        days_in_month = 31  # Valor máximo - ajuste conforme necessário
        complete_daily_data = {}
        for day in range(1, days_in_month + 1):
            day_str = f"{day:02d}"
            complete_daily_data[day_str] = daily_data.get(day_str, {'total': 0, 'status': 'none'})

        # Consultas totais
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

        saldo = total_pago + total_previsto  # Cálculo correto do saldo

        # Valores vencidos e a vencer
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

        # Consulta lançamentos
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

        # Processamento dos lançamentos
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

        print("DEBUG → Lançamentos enviados:")
        print(lancamentos)

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

# ROTAS DE AÇÃO DOS BOTÕES
@app.route("/marcar_pago", methods=["POST"])
def marcar_pago():
    try:
        id_lancamento = request.args.get("codigo")
        conn = sqlite3.connect("grupo_fisgar.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE contas_a_pagar SET valor_pago = valor WHERE codigo = ?", (id_lancamento,))
        conn.commit()
        return "", 200
    except Exception as e:
        print("Erro ao marcar como pago:", e)
        return "", 500
    finally:
        conn.close()


@app.route("/excluir", methods=["POST"])
def excluir():
    try:
        id_lancamento = request.args.get("codigo")
        conn = sqlite3.connect("grupo_fisgar.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contas_a_pagar WHERE codigo = ?", (id_lancamento,))
        conn.commit()
        return "", 200
    except Exception as e:
        print("Erro ao excluir:", e)
        return "", 500
    finally:

        @app.route("/editar", methods=["POST"])
        def editar():
            try:
                data = request.get_json()
                conn = sqlite3.connect("grupo_fisgar.db")
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE contas_a_pagar
                    SET fornecedor = ?, categorias = ?, plano_de_contas = ?, vencimento = ?, valor = ?
                    WHERE codigo = ?
                """, (
                    data["fornecedor"],
                    data["categoria"],
                    data["plano"],
                    data["vencimento"],
                    data["valor"],
                    data["codigo"]
                ))

                conn.commit()
                return "", 200
            except Exception as e:
                print("Erro ao editar lançamento:", e)
                return "", 500
            finally:
                conn.close()
                from flask import Flask, render_template

        conn.close()
@app.route("/lancamento_manual")
def lancamento_manual():
    return render_template("lancamento_manual.html")
from datetime import datetime, date
import sqlite3
import json

app = Flask(__name__)

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

# Conexão com o banco
def get_db_connection():
    conn = sqlite3.connect("C:/sistema_financeiro/grupo_fisgar.db")
    conn.row_factory = sqlite3.Row  # Converte para dicionário
    return conn

# Rota de Indicadores
@app.route("/indicadores")
def indicadores():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        hoje = datetime.today()
        mes_param = request.args.get("mes", hoje.month)
        ano_param = request.args.get("ano", hoje.year)
        filtro = request.args.get("filtro", "mes")

        # Garante que mes/ano são strings com 2 dígitos
        mes_corrente = f"{int(mes_param):02d}/{ano_param}"

        # Consulta para obter os dias do mês com pagamentos
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

        # Processa os resultados para o formato diário
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

        # Preenche os dias sem lançamentos com zero
        days_in_month = 31
        complete_daily_data = {}
        for day in range(1, days_in_month + 1):
            day_str = f"{day:02d}"
            complete_daily_data[day_str] = daily_data.get(day_str, {'total': 0, 'status': 'none'})

        # Consultas totais
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

        # Valores vencidos e a vencer
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

        # Consulta lançamentos
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

        # Processamento dos lançamentos
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

# Rota do Lançamento Manual
@app.route("/lancamento_manual", methods=["GET", "POST"])
def lancamento_manual():
    conn = get_db_connection()

    if request.method == "POST":
        try:
            # Pega todos os campos do formulário
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
                'status': request.form.get('status') or calcular_status(request.form.get('vencimento'), request.form.get('valor_pago')),
                'documento': request.form.get('documento'),
                'tipo_documento': request.form.get('tipo_documento'),
                'pagamento_tipo': request.form.get('pagamento_tipo'),
                'comentario': request.form.get('comentario'),
                'data_cadastro': datetime.now().strftime('%d/%m/%Y'),
                'data_competencia': request.form.get('data_competencia'),
                'data_documento': request.form.get('data_documento')
            }

            # Query com todas as colunas do banco
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

    # Para GET: Busca opções para os selects
    try:
        campos_select = {
            'fornecedores': conn.execute("SELECT DISTINCT fornecedor FROM contas_a_pagar WHERE fornecedor IS NOT NULL").fetchall(),
            'categorias': conn.execute("SELECT DISTINCT categorias FROM contas_a_pagar WHERE categorias IS NOT NULL").fetchall(),
            'planos': conn.execute("SELECT DISTINCT plano_de_contas FROM contas_a_pagar WHERE plano_de_contas IS NOT NULL").fetchall(),
            'centros_custo': conn.execute("SELECT DISTINCT centro_de_custo FROM contas_a_pagar WHERE centro_de_custo IS NOT NULL").fetchall(),
            'empresas': conn.execute("SELECT DISTINCT empresa FROM contas_a_pagar WHERE empresa IS NOT NULL").fetchall(),
            'contas': conn.execute("SELECT DISTINCT conta FROM contas_a_pagar WHERE conta IS NOT NULL").fetchall(),
            'tipos_custo': conn.execute("SELECT DISTINCT tipo_custo FROM contas_a_pagar WHERE tipo_custo IS NOT NULL").fetchall(),
            'tipos': conn.execute("SELECT DISTINCT tipo FROM contas_a_pagar WHERE tipo IS NOT NULL").fetchall(),
            'tipos_doc': conn.execute("SELECT DISTINCT tipo_documento FROM contas_a_pagar WHERE tipo_documento IS NOT NULL").fetchall(),
            'formas_pagto': conn.execute("SELECT DISTINCT pagamento_tipo FROM contas_a_pagar WHERE pagamento_tipo IS NOT NULL").fetchall()
        }

        opcoes = {k: [item[0] for item in v] for k, v in campos_select.items()}

        return render_template("lancamento_manual.html", **opcoes)

    except Exception as e:
        flash(f"Erro ao carregar opções: {str(e)}", "danger")
        return render_template("lancamento_manual.html")
    finally:
        conn.close()


# Rotas de ação
@app.route("/marcar_pago", methods=["POST"])
def marcar_pago():
    try:
        id_lancamento = request.args.get("codigo")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE contas_a_pagar SET valor_pago = valor WHERE codigo = ?", (id_lancamento,))
        conn.commit()
        return "", 200
    except Exception as e:
        print("Erro ao marcar como pago:", e)
        return "", 500
    finally:
        conn.close()

@app.route("/excluir", methods=["POST"])
def excluir():
    try:
        id_lancamento = request.args.get("codigo")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contas_a_pagar WHERE codigo = ?", (id_lancamento,))
        conn.commit()
        return "", 200
    except Exception as e:
        print("Erro ao excluir:", e)
        return "", 500
    finally:
        conn.close()

@app.route("/editar", methods=["POST"])
def editar():
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE contas_a_pagar
            SET fornecedor = ?, categorias = ?, plano_de_contas = ?, vencimento = ?, valor = ?
            WHERE codigo = ?
        """, (
            data["fornecedor"],
            data["categoria"],
            data["plano"],
            data["vencimento"],
            data["valor"],
            data["codigo"]
        ))

        conn.commit()
        return "", 200
    except Exception as e:
        print("Erro ao editar lançamento:", e)
        return "", 500
    finally:
        conn.close()


@app.route("/editar_massa", methods=["POST"])
def editar_massa():
    try:
        # Obter os dados JSON da requisição
        dados = request.get_json()

        # Validar os dados recebidos
        if not dados or 'ids' not in dados:
            return jsonify({"success": False, "error": "Dados inválidos ou nenhum ID fornecido"}), 400

        # Conectar ao banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()

        # Iniciar a construção da query SQL
        updates = []
        params = []

        # Campos que podem ser atualizados em massa (ajustados para seu modelo)
        campos_editaveis = {
            'status': dados.get('status'),
            'vencimento': dados.get('vencimento'),
            'fornecedor': dados.get('fornecedor'),
            'categorias': dados.get('categorias'),
            'plano_de_contas': dados.get('plano_de_contas'),
            'valor': dados.get('valor'),
            'comentario': dados.get('comentario'),
            'valor_pago': None  # Tratamento especial abaixo
        }

        # Se status for 'paid', marcar valor_pago como igual ao valor
        if dados.get('status') == 'paid':
            campos_editaveis['valor_pago'] = 'valor'

        # Construir a parte SET da query
        for campo, valor in campos_editaveis.items():
            if valor is not None:
                if campo == 'valor_pago' and valor == 'valor':
                    updates.append("valor_pago = valor")
                elif valor:  # Só adiciona se não for vazio/nulo
                    updates.append(f"{campo} = ?")
                    params.append(valor)

        # Verificar se há campos para atualizar
        if not updates:
            return jsonify({"success": False, "error": "Nenhum campo válido para atualização"}), 400

        # Adicionar os IDs (codigos) dos registros a serem atualizados
        placeholders = ','.join(['?'] * len(dados['ids']))
        query = f"UPDATE contas_a_pagar SET {', '.join(updates)} WHERE codigo IN ({placeholders})"
        params.extend(dados['ids'])

        # Executar a atualização
        cursor.execute(query, params)
        conn.commit()

        # Verificar se alguma linha foi afetada
        if cursor.rowcount == 0:
            return jsonify({"success": False, "error": "Nenhum registro foi atualizado"}), 400

        return jsonify({
            "success": True,
            "message": f"{cursor.rowcount} registros atualizados com sucesso",
            "updated": cursor.rowcount
        })

    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"success": False, "error": f"Erro no banco de dados: {str(e)}"}), 500
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return jsonify({"success": False, "error": f"Erro inesperado: {str(e)}"}), 500
    finally:
        if 'conn' in locals():
            conn.close()
if __name__ == "__main__":
    app.run(debug=True)
