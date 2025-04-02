from flask import render_template, request
import sqlite3
import plotly
import plotly.graph_objs as go
import json
from datetime import datetime, timedelta

def contas_a_pagar():
    conexao = sqlite3.connect("grupo_fisgar.db")
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT vencimento, valor, valor_pago, status
        FROM contas_a_pagar
    """)

    # 🗓️ Filtros de datas
    hoje = datetime.today()
    data_de = request.args.get("data_de")
    data_ate = request.args.get("data_ate")

    if not data_de:
        data_de = hoje.replace(day=1).strftime("%Y-%m-%d")
    if not data_ate:
        data_ate = hoje.strftime("%Y-%m-%d")

    # 🔍 Buscar dados filtrados
    cursor.execute("""
        SELECT fornecedor, vencimento, valor, valor_pago, status, categorias, tipo, centro_de_custo, codigo
        FROM contas_a_pagar
        WHERE date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2))
        BETWEEN ? AND ?
    """, (data_de, data_ate))
    registros = cursor.fetchall()

    dados = []
    total_previsto = 0
    total_pago = 0

    for r in registros:
        fornecedor, vencimento, valor, valor_pago, status, categoria, tipo, centro, codigo = r
        valor = float(valor or 0)
        valor_pago = float(valor_pago or 0)
        pendente = valor + valor_pago  # valor é negativo
        dados.append([fornecedor, vencimento, valor, valor_pago, pendente, status, categoria, tipo, centro, codigo])
        total_previsto += valor
        total_pago += valor_pago

    saldo = total_previsto + total_pago

    # 📌 Contas de hoje / atraso / amanhã
    hoje_str = hoje.strftime("%d/%m/%Y")
    amanha_str = (hoje + timedelta(days=1)).strftime("%d/%m/%Y")

    cursor.execute("SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar WHERE vencimento = ? AND status != 'Pago'", (hoje_str,))
    total_hoje = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar 
        WHERE date(substr(vencimento,7,4)||'-'||substr(vencimento,4,2)||'-'||substr(vencimento,1,2)) < ?
        AND status != 'Pago'
    """, (hoje.strftime("%Y-%m-%d"),))
    total_atraso = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar WHERE vencimento = ? AND status != 'Pago'", (amanha_str,))
    total_amanha = cursor.fetchone()[0] or 0

    totais = {
        "previsto": f"{total_previsto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "pago": f"{total_pago:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "saldo": f"{saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "atraso": f"{total_atraso:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "hoje": f"{total_hoje:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "amanha": total_amanha
    }

    # 📊 Gráfico por Status
    cursor.execute("""
        SELECT status, SUM(CAST(valor AS FLOAT)) 
        FROM contas_a_pagar 
        WHERE date(substr(vencimento,7,4)||'-'||substr(vencimento,4,2)||'-'||substr(vencimento,1,2)) 
        BETWEEN ? AND ?
        GROUP BY status
    """, (data_de, data_ate))
    status_dados = cursor.fetchall()
    fig_status = go.Figure([go.Bar(x=[r[0] for r in status_dados], y=[r[1] for r in status_dados])])
    grafico_status = json.dumps(fig_status, cls=plotly.utils.PlotlyJSONEncoder)

    # 📊 Gráfico por Categoria
    cursor.execute("""
        SELECT categorias, SUM(CAST(valor AS FLOAT)) 
        FROM contas_a_pagar 
        WHERE date(substr(vencimento,7,4)||'-'||substr(vencimento,4,2)||'-'||substr(vencimento,1,2)) 
        BETWEEN ? AND ?
        GROUP BY categorias
    """, (data_de, data_ate))
    categoria_dados = cursor.fetchall()
    fig_categoria = go.Figure([go.Pie(labels=[r[0] for r in categoria_dados], values=[r[1] for r in categoria_dados])])
    grafico_categoria = json.dumps(fig_categoria, cls=plotly.utils.PlotlyJSONEncoder)

    # 📈 Gráfico Contas por Dia
    cursor.execute("""
        SELECT vencimento, SUM(CAST(valor AS FLOAT)) 
        FROM contas_a_pagar 
        WHERE date(substr(vencimento,7,4)||'-'||substr(vencimento,4,2)||'-'||substr(vencimento,1,2)) 
        BETWEEN ? AND ?
        GROUP BY vencimento
    """, (data_de, data_ate))
    dia_dados = cursor.fetchall()
    fig_dia = go.Figure([go.Scatter(x=[r[0] for r in dia_dados], y=[r[1] for r in dia_dados], mode="lines+markers")])
    grafico_dia = json.dumps(fig_dia, cls=plotly.utils.PlotlyJSONEncoder)

    conexao.close()

    graficos = {
        "status": grafico_status,
        "categoria": grafico_categoria,
        "dia": grafico_dia
    }

    # Criação dos gráficos
    fig_linhas = go.Figure()
    # ... (código do gráfico de linhas)
    # Agrupar valores por categoria
    dados_categoria = {}
    for r in registros:
        print("Total de colunas retornadas:", len(r))
        valor = r[1]  # índice da coluna 'valor'
        try:
            valor = float(str(valor).replace(",", "."))
        except:
            valor = 0
        if categoria in dados_categoria:
            dados_categoria[categoria] += valor
        else:
            dados_categoria[categoria] = valor

    categorias = list(dados_categoria.keys())
    valores_categoria = list(abs(v) for v in dados_categoria.values())

    fig_categoria = go.Figure()
    fig_categoria.add_trace(go.Pie(labels=categorias, values=valores_categoria))

    # Converte os gráficos em JSON para o template
    grafico_linhas_json = json.dumps(fig_linhas, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_categoria_json = json.dumps(fig_categoria, cls=plotly.utils.PlotlyJSONEncoder)

    # 💰 Formata os totais no padrão brasileiro e envia pro template
    totais = {
        "previsto": f"{total_previsto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "pago": f"{total_pago:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "saldo": f"{saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "atraso": f"{total_atraso:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "hoje": f"{total_hoje:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "amanha": f"{total_amanha:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    }
    # Gráfico de Status (com segurança e sem erro)
    dados_status = {}
    for r in registros:
        try:
            status = r[6]  # índice da coluna 'status'
            valor = float(str(r[2]).replace(",", ".") or 0)  # índice da coluna 'valor'
            if status:
                dados_status[status] = dados_status.get(status, 0) + abs(valor)
        except:
            continue

    fig_status = go.Figure()
    fig_status.add_trace(go.Pie(
        labels=list(dados_status.keys()),
        values=list(dados_status.values())
    ))
    grafico_status_json = json.dumps(fig_status, cls=plotly.utils.PlotlyJSONEncoder)

    # Envia pro HTML

    return render_template("contas_a_pagar.html",
                           total_previsto=total_previsto,
                           total_pago=total_pago,
                           saldo=saldo,
                           total_atraso=total_atraso,
                           registros=registros,
                           data_de=data_de,
                           data_ate=data_ate,
                           grafico_linhas=grafico_linhas_json,
                           grafico_categoria=grafico_categoria_json,
                           totais=totais,
                           graficos={
                               "status": grafico_status_json,
                               "categoria": grafico_categoria_json,
                               "linhas": grafico_linhas_json
                           }
                           )







