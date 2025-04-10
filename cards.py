from flask import Flask, render_template, request
import sqlite3
from datetime import datetime

app = Flask(__name__)

def formatar_valor(valor):
    try:
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return "R$ 0,00"

@app.route("/indicadores")
def indicadores():
    conn = sqlite3.connect("C:/sistema_financeiro/grupo_fisgar.db")
    cursor = conn.cursor()

    hoje = datetime.today()
    dia_hoje = hoje.strftime('%d/%m/%Y')
    data_sql = hoje.strftime('%Y-%m-%d')
    mes_corrente = hoje.strftime('%m/%Y')

    filtro = request.args.get("filtro", "mes")

    # Cards
    cursor.execute("""
        SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
        WHERE SUBSTR(vencimento, 4, 7) = ?
    """, (mes_corrente,))
    total_previsto = cursor.fetchone()[0] or 0.0

    cursor.execute("""
        SELECT SUM(CAST(valor_pago AS FLOAT)) FROM contas_a_pagar
        WHERE SUBSTR(vencimento, 4, 7) = ?
    """, (mes_corrente,))
    total_pago = cursor.fetchone()[0] or 0.0

    saldo = total_pago + total_previsto

    cursor.execute("""
        SELECT COUNT(*) FROM contas_a_pagar 
        WHERE (valor_pago IS NULL OR valor_pago = 0)
        AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now')
    """)
    vencidas = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM contas_a_pagar 
        WHERE (valor_pago IS NULL OR valor_pago = 0)
        AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) = date('now')
    """)
    a_pagar_hoje = cursor.fetchone()[0]

    # Filtrar lançamentos conforme botão clicado
    if filtro == "atrasadas":
        titulo_lancamentos = "Contas Vencidas"
        cursor.execute("""
            SELECT vencimento, categorias, fornecedor, plano_de_contas, valor, valor_pago
            FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
            AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now')
            ORDER BY vencimento ASC
        """)
    elif filtro == "hoje":
        titulo_lancamentos = "Contas a Pagar Hoje"
        cursor.execute("""
            SELECT vencimento, categorias, fornecedor, plano_de_contas, valor, valor_pago
            FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
            AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) = date('now')
            ORDER BY vencimento ASC
        """)
    else:
        titulo_lancamentos = f"Lançamentos de {mes_corrente}"
        cursor.execute("""
            SELECT vencimento, categorias, fornecedor, plano_de_contas, valor, valor_pago
            FROM contas_a_pagar
            WHERE SUBSTR(vencimento, 4, 7) = ?
            ORDER BY vencimento ASC
        """, (mes_corrente,))

    lancamentos = cursor.fetchall()
    lancamentos = [
        (v, c, f, p, float(val or 0), float(pago or 0))
        for v, c, f, p, val, pago in lancamentos
    ]

    conn.close()

    return render_template("teste_cards.html",
                           total_previsto=formatar_valor(total_previsto),
                           total_pago=formatar_valor(total_pago),
                           saldo=formatar_valor(saldo),
                           vencidas=vencidas,
                           a_vencer=a_pagar_hoje,
                           lancamentos=lancamentos,
                           mes_corrente=mes_corrente,
                           titulo_lancamentos=titulo_lancamentos)


if __name__ == "__main__":
    app.run(debug=True)
