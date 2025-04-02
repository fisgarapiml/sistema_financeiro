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


    # Inicializa os totais
    total_previsto = 0
    total_pago = 0
    saldo = 0
    total_atraso = 0
    total_hoje = 0
    total_amanha = 0

    hoje = datetime.now().date()
    amanha = hoje + timedelta(days=1)

    for r in registros:
        try:
            vencimento_str = r[1]  # vencimento
            valor = float(str(r[2]).replace(",", ".") or 0)
            valor_pago = float(str(r[3]).replace(",", ".") or 0)

            vencimento = datetime.strptime(vencimento_str, "%d/%m/%Y").date()

            total_previsto += valor
            total_pago += valor_pago
            saldo += valor_pago + valor  # valor é negativo

            if vencimento == hoje:
                total_hoje += abs(valor)

            if vencimento == amanha:
                total_amanha += abs(valor)

            if vencimento < hoje and valor_pago == 0:
                total_atraso += abs(valor)

        except Exception as e:
            print("Erro ao processar linha:", e)
            continue
            # Prepara os lançamentos organizados por categoria
            lancamentos_por_categoria = {}
            for r in registros:
                try:
                    fornecedor = r[0]
                    vencimento = r[1]
                    valor = float(str(r[2]).replace(",", ".") or 0)
                    status = r[4]
                    categoria = r[5]

                    if categoria not in lancamentos_por_categoria:
                        lancamentos_por_categoria[categoria] = []

                    lancamentos_por_categoria[categoria].append({
                        "fornecedor": fornecedor,
                        "vencimento": vencimento,
                        "valor": f"R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                        "status": status
                    })
                except:
                    continue

    # Gráfico de linhas (você pode adicionar aqui sua lógica)
    fig_linhas = go.Figure()

    # Gráfico de Categorias
    dados_categoria = {}
    for r in registros:
        try:
            categoria = r[7]  # índice da coluna 'categorias'
            valor = float(str(r[2]).replace(",", ".") or 0)
            if categoria:
                dados_categoria[categoria] = dados_categoria.get(categoria, 0) + abs(valor)
        except:
            continue

    categorias = list(dados_categoria.keys())
    valores_categoria = list(dados_categoria.values())

    fig_categoria = go.Figure()
    fig_categoria.add_trace(go.Pie(labels=categorias, values=valores_categoria))

    # Gráfico de Status
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

    # Converte os gráficos para JSON
    grafico_linhas_json = json.dumps(fig_linhas, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_categoria_json = json.dumps(fig_categoria, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_status_json = json.dumps(fig_status, cls=plotly.utils.PlotlyJSONEncoder)

    # Totais formatados
    totais = {
        "previsto": f"{total_previsto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "pago": f"{total_pago:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "saldo": f"{saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "atraso": f"{total_atraso:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "hoje": f"{total_hoje:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "amanha": f"{total_amanha:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    }

    # Gráfico por Dia (agrupa por vencimento)
    from collections import defaultdict
    dados_dia = defaultdict(float)
    for r in registros:
        try:
            vencimento = r[0]  # índice da coluna vencimento
            valor = float(str(r[1]).replace(",", ".") or 0)  # índice da coluna valor
            if vencimento:
                dados_dia[vencimento] += abs(valor)
        except:
            continue

    dias = sorted(dados_dia.keys())
    valores_por_dia = [dados_dia[d] for d in dias]

    fig_dia = go.Figure()
    fig_dia.add_trace(go.Bar(x=dias, y=valores_por_dia))

    # Converte os gráficos para JSON
    grafico_linhas_json = json.dumps(fig_linhas, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_categoria_json = json.dumps(fig_categoria, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_status_json = json.dumps(fig_status, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_dia_json = json.dumps(fig_dia, cls=plotly.utils.PlotlyJSONEncoder)

    # Totais formatados
    totais = {
        "previsto": f"{total_previsto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "pago": f"{total_pago:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "saldo": f"{saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "atraso": f"{total_atraso:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "hoje": f"{total_hoje:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "amanha": f"{total_amanha:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    }
    print("Colunas do primeiro registro:", registros[0])
    print("Total de colunas:", len(registros[0]))

    # Gráfico de Status (com segurança e sem erro)
    dados_status = {}
    for r in registros:
        try:
            status = r[4]  # índice da coluna 'status'
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
    # 🔍 Cria um resumo dos lançamentos por categoria
    lancamentos_por_categoria = {}
    for r in registros:
        try:
            categoria = r[5]  # índice da coluna 'categorias'
            valor = float(str(r[2]).replace(",", ".") or 0)
            if categoria not in lancamentos_por_categoria:
                lancamentos_por_categoria[categoria] = []
            lancamentos_por_categoria[categoria].append({
                "fornecedor": r[0],
                "vencimento": r[1],
                "valor": valor,
                "status": r[4]
            })
        except:
            continue

    # Envia pro HTML

    # Envio dos dados pro template
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
                           grafico_status=grafico_status_json,
                           grafico_dia=grafico_dia_json,
                           totais=totais,  # ✅ necessário para os cards
                           lancamentos_categoria=lancamentos_por_categoria  # ✅ para interatividade futura
                           )












