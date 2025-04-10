from flask import Flask, render_template, request
from datetime import datetime, date
import sqlite3

app = Flask(__name__)


def formatar_brl(valor):
    """Formata valores monetários no padrão brasileiro"""
    try:
        valor_float = float(valor) if valor is not None else 0.0
        return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"


@app.route("/indicadores")
def indicadores():
    conn = sqlite3.connect("C:/sistema_financeiro/grupo_fisgar.db")
    cursor = conn.cursor()

    hoje = datetime.today()
    mes_param = request.args.get("mes", hoje.month)
    ano_param = request.args.get("ano", hoje.year)
    filtro = request.args.get("filtro", "mes")

    # Garante que mes/ano são strings com 2 dígitos
    mes_corrente = f"{int(mes_param):02d}/{ano_param}"

    # Consultas seguras com tratamento de None
    def get_sql_result(query, params=()):
        cursor.execute(query, params)
        result = cursor.fetchone()[0]
        return float(result) if result is not None else 0.0

    # Totais
    total_previsto = get_sql_result("""
        SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
        WHERE SUBSTR(vencimento, 4, 7) = ?
    """, (mes_corrente,))

    total_pago = get_sql_result("""
        SELECT SUM(CAST(valor_pago AS FLOAT)) FROM contas_a_pagar
        WHERE SUBSTR(vencimento, 4, 7) = ?
    """, (mes_corrente,))

    saldo = total_previsto - total_pago  # Corrigido: saldo = previsto - pago

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

    # Lançamentos conforme filtro
    query_lancamentos = """
        SELECT vencimento, categorias, fornecedor, plano_de_contas, valor, valor_pago
        FROM contas_a_pagar
        WHERE 1=1
    """

    params = []
    if filtro == "atrasadas":
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
        query_lancamentos += " AND SUBSTR(vencimento, 4, 7) = ?"
        params.append(mes_corrente)

    query_lancamentos += " ORDER BY vencimento ASC"
    cursor.execute(query_lancamentos, params)

    # Processamento seguro dos lançamentos
    lancamentos = []
    for v, c, f, p, val, pago in cursor.fetchall():
        lancamentos.append((
            v,
            c or '-',
            f or '-',
            p or '-',
            float(val) if val is not None else 0.0,
            float(pago) if pago is not None else 0.0
        ))

    conn.close()

    return render_template(
        "teste_cards.html",
        total_previsto=total_previsto,  # Envia como float para cálculos
        total_pago=total_pago,
        saldo=saldo,
        vencidas=valor_vencido_total,
        a_vencer=valor_hoje_total,
        lancamentos=lancamentos,
        mes_corrente=mes_corrente,
        titulo_lancamentos=titulo_lancamentos,
        hoje_data=date.today(),
        datetime=datetime,
        formatar_brl=formatar_brl  # Passa a função para o template
    )


if __name__ == "__main__":
    app.run(debug=True)