from flask import Blueprint, render_template, request, redirect
import sqlite3
from datetime import datetime

def formatar_valor(valor):
    try:
        valor = float(valor)
        return f"{valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return "0,00"

lancamentos_bp = Blueprint("lancamentos", __name__)

@lancamentos_bp.route("/lancamentos", methods=["GET", "POST"])
def lancamentos():
    conn = sqlite3.connect("grupo_fisgar.db")
    cursor = conn.cursor()

    hoje = datetime.today()
    status_filtro = request.args.get("status", "Todos")
    data_inicio = request.args.get("inicio")
    data_fim = request.args.get("fim")

    if not data_inicio:
        data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
    if not data_fim:
        data_fim = hoje.strftime("%Y-%m-%d")

    # 📌 BAIXA INDIVIDUAL
    if request.method == "POST" and request.form.get("acao") == "baixar_individual":
        codigo = request.form.get("codigo")
        valor_pago = request.form.get("valor_pago", "0").replace(",", ".")
        data_pagamento = request.form.get("data_pagamento")
        cursor.execute("""
            UPDATE contas_a_pagar
            SET valor_pago = ?, data_pagamento = ?, status = 'Pago'
            WHERE codigo = ?
        """, (valor_pago, data_pagamento, codigo))
        conn.commit()
        return redirect(request.url)

    # 📌 BAIXA EM MASSA
    if request.method == "POST" and request.form.get("acao") == "baixar_em_massa":
        codigos = request.form.getlist("codigos")
        valor_padrao = request.form.get("valor_padrao", "0").replace(",", ".")
        data_padrao = request.form.get("data_padrao")
        for codigo in codigos:
            cursor.execute("""
                UPDATE contas_a_pagar
                SET valor_pago = ?, data_pagamento = ?, status = 'Pago'
                WHERE codigo = ?
            """, (valor_padrao, data_padrao, codigo))
        conn.commit()
        return redirect(request.url)

    # 🔎 CONSULTA GERAL
    cursor.execute("""
        SELECT codigo, fornecedor, categorias, centro_de_custo, tipo,
               vencimento, valor, valor_pago, status, plano_de_contas
        FROM contas_a_pagar
    """)
    dados = cursor.fetchall()
    conn.close()

    dados_filtrados = []
    for d in dados:
        try:
            vencimento_data = datetime.strptime(d[5], "%d/%m/%Y").date()
        except:
            continue

        if status_filtro == "Atrasados":
            if d[8] not in ("Aberto", "Pendente", "Pago Parcialmente"):
                continue
            if vencimento_data >= hoje.date():
                continue
        else:
            if data_inicio and vencimento_data < datetime.strptime(data_inicio, "%Y-%m-%d").date():
                continue
            if data_fim and vencimento_data > datetime.strptime(data_fim, "%Y-%m-%d").date():
                continue
            if status_filtro != "Todos" and d[8] != status_filtro:
                continue

        dados_filtrados.append(d)

    totais = {
        "total": sum(-float(d[6]) for d in dados_filtrados),
        "pagos": sum(-float(d[6]) for d in dados_filtrados if d[8] == "Pago"),
        "pendentes": sum(-float(d[6]) for d in dados_filtrados if d[8] in ("Aberto", "Pendente", "Pago Parcialmente")),
        "hoje": sum(-float(d[6]) for d in dados_filtrados if d[5] == hoje.strftime("%d/%m/%Y")),
        "atrasados": sum(-float(d[6]) for d in dados_filtrados if
                         d[8] in ("Aberto", "Pendente", "Pago Parcialmente") and
                         datetime.strptime(d[5], "%d/%m/%Y").date() < hoje.date())
    }

    lista_lancamentos = []
    for d in dados_filtrados:
        lista_lancamentos.append({
            "codigo": d[0],
            "fornecedor": d[1],
            "categoria": d[2],
            "centro": d[3],
            "tipo": d[4],
            "vencimento": d[5],
            "valor": formatar_valor(d[6]),
            "valor_pago": formatar_valor(d[7]),
            "status": d[8],
            "plano": d[9],
            "raw_valor": d[6],
            "raw_valor_pago": d[7]
        })

    return render_template("lancamento_manual.html",
                           lancamentos=lista_lancamentos,
                           totais=totais,
                           data_de=data_inicio,
                           data_ate=data_fim,
                           status=status_filtro,
                           hoje=hoje.strftime("%Y-%m-%d"))
