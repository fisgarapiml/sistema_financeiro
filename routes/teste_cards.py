from flask import Blueprint, render_template
import sqlite3
from datetime import datetime

bp_cards = Blueprint('cards_indicadores', __name__)

def formatar_valor(valor):
    try:
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return "R$ 0,00"

@bp_cards.route("/indicadores")
def exibir_cards_indicadores():
    conn = sqlite3.connect("C:/sistema_financeiro/grupo_fisgar.db")
    cursor = conn.cursor()

    # Total Previsto a Pagar
    cursor.execute("SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar")
    total_previsto = cursor.fetchone()[0] or 0.0

    # Total Pago
    cursor.execute("SELECT SUM(CAST(valor_pago AS FLOAT)) FROM contas_a_pagar")
    total_pago = cursor.fetchone()[0] or 0.0

    # Saldo do Mês
    saldo = total_pago + total_previsto

    # Contas Vencidas
    cursor.execute("""
        SELECT COUNT(*) FROM contas_a_pagar 
        WHERE (valor_pago IS NULL OR valor_pago = 0)
        AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now')
    """)
    vencidas = cursor.fetchone()[0]

    # Contas a Vencer
    cursor.execute("""
        SELECT COUNT(*) FROM contas_a_pagar 
        WHERE (valor_pago IS NULL OR valor_pago = 0)
        AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) >= date('now')
    """)
    a_vencer = cursor.fetchone()[0]

    conn.close()

    from flask import request
    from datetime import datetime as dt

    return render_template("cards_indicadores.html",
                           total_previsto=formatar_valor(total_previsto),
                           total_pago=formatar_valor(total_pago),
                           saldo=formatar_valor(saldo),
                           vencidas=vencidas,
                           a_vencer=a_vencer,
                           lancamentos=lancamentos,
                           titulo_lancamentos=titulo_lancamentos,
                           now=dt.now,
                           request=request
                           )

