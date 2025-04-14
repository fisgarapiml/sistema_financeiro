from flask import Flask, render_template, request, url_for
from datetime import datetime, date
import sqlite3
import json
from contextlib import closing

app = Flask(__name__)
app.config['DATABASE_PATH'] = "C:/sistema_financeiro/grupo_fisgar.db"


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
        return 'overdue' if vencimento < hoje else 'pending'
    except (ValueError, AttributeError):
        return 'pending'


def get_db_connection():
    """Retorna uma conexão com o banco de dados"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    """Rota principal que redireciona para /indicadores"""
    return indicadores()


@app.route("/indicadores")
def indicadores():
    try:
        hoje = datetime.today()
        mes_param = request.args.get("mes", hoje.month, type=int)
        ano_param = request.args.get("ano", hoje.year, type=int)
        filtro = request.args.get("filtro", "mes")

        mes_corrente = f"{mes_param:02d}/{ano_param}"

        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()

            # Consulta para dados diários
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
                dia = row['dia']
                if dia in daily_data:
                    daily_data[dia]['total'] += row['total']
                    if row['status'] == 'overdue' or (
                            row['status'] == 'pending' and daily_data[dia]['status'] == 'paid'):
                        daily_data[dia]['status'] = row['status']
                else:
                    daily_data[dia] = {'total': row['total'], 'status': row['status']}

            # Preenche dias sem lançamentos
            complete_daily_data = {
                f"{day:02d}": daily_data.get(f"{day:02d}", {'total': 0, 'status': 'none'})
                for day in range(1, 32)
            }

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
                SELECT COALESCE(SUM(CAST(valor_pago AS FLOAT)), 0) FROM contas_a_pagar
                WHERE substr(vencimento, 4, 7) = ?
                """, (mes_corrente,))

            saldo = total_pago - total_previsto

            # Consulta lançamentos
            query_base = """
                SELECT 
                    vencimento, 
                    categorias, 
                    fornecedor, 
                    plano_de_contas, 
                    valor, 
                    valor_pago,
                    id
                FROM contas_a_pagar
                WHERE 1=1
                """

            conditions = {
                "atrasados": """
                    AND (valor_pago IS NULL OR valor_pago = 0)
                    AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now')
                    """,
                "hoje": """
                    AND (valor_pago IS NULL OR valor_pago = 0)
                    AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) = date('now')
                    """
            }

            titulos = {
                "atrasados": "Contas Vencidas",
                "hoje": "Contas a Pagar Hoje",
                "mes": f"Lançamentos de {mes_corrente}"
            }

            query = query_base + conditions.get(filtro, " AND substr(vencimento, 4, 7) = ?")
            params = () if filtro in conditions else (mes_corrente,)

            cursor.execute(query + " ORDER BY vencimento ASC", params)

            lancamentos = [{
                'id': row['id'],
                'vencimento': row['vencimento'],
                'categoria': row['categorias'] or '-',
                'fornecedor': row['fornecedor'] or '-',
                'plano': row['plano_de_contas'] or '-',
                'valor': float(row['valor'] or 0),
                'pago': float(row['valor_pago'] or 0),
                'status': calcular_status(row['vencimento'], row['valor_pago'])
            } for row in cursor]

        return render_template(
            "dashboard_contas_a_pagar.html",
            total_previsto=total_previsto,
            total_pago=total_pago,
            saldo=saldo,
            vencidas=get_sql_result("""
                SELECT COALESCE(SUM(CAST(valor AS FLOAT)), 0) FROM contas_a_pagar
                WHERE (valor_pago IS NULL OR valor_pago = 0)
                AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now')
                """),
            a_vencer=get_sql_result("""
                SELECT COALESCE(SUM(CAST(valor AS FLOAT)), 0) FROM contas_a_pagar
                WHERE (valor_pago IS NULL OR valor_pago = 0)
                AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) = date('now')
                """),
            lancamentos=lancamentos,
            titulo_lancamentos=titulos.get(filtro, titulos['mes']),
            formatar_brl=formatar_brl,
            daily_payments=json.dumps(complete_daily_data),
            current_month=mes_param,
            current_year=ano_param,
            mes_corrente=mes_corrente
        )


    except Exception as e:
        app.logger.error(f"Erro na rota /indicadores: {str(e)}", exc_info=True)
        return render_template("error.html", error=str(e)), 500

from flask import Flask, render_template

@app.route("/lancamento_manual")
def lancamento_manual():
    return render_template("lancamento_manual.html")

if __name__ == "__main__":
    app.run(debug=True)