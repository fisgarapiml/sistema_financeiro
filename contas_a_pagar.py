from flask import render_template, request
import sqlite3
import plotly
import plotly.graph_objs as go
import json
from datetime import datetime, timedelta
from collections import defaultdict

def contas_a_pagar():
    conexao = sqlite3.connect('grupo_fisgar.db')
    cursor = conexao.cursor()

    cursor.execute("SELECT * FROM contas_a_pagar")
    dados = cursor.fetchall()

    def gerar_grafico_por_centro(dados):
        agrupado = defaultdict(float)
        for linha in dados:
            try:
                centro = linha[8] if linha[8] else 'Indefinido'  # Centro de Custo = l[8]
                valor = float(linha[2]) if linha[2] else 0  # Valor = l[2]
                agrupado[centro] += abs(valor)
            except Exception as e:
                print("Erro ao processar linha:", linha)
                print("Erro:", e)

        grafico = {
            'data': [{
                'x': list(agrupado.keys()),
                'y': list(agrupado.values()),
                'type': 'bar',
                'marker': {'color': '#0d6efd'}
            }],
            'layout': {
                'title': 'Total por Centro de Custo',
                'xaxis': {'title': 'Centro de Custo'},
                'yaxis': {'title': 'Total (R$)'},
                'margin': {'t': 40, 'b': 60}
            }
        }

        return json.dumps(grafico)

    grafico_centro = gerar_grafico_por_centro(dados)

    # ✅ Aqui entra a linha nova
    grafico_centro = gerar_grafico_por_centro(dados)
    print("🔍 Gráfico Centro de Custo:", grafico_centro)

    # Datas de filtro
    hoje = datetime.today()
    data_de = request.args.get("data_de") or hoje.replace(day=1).strftime("%Y-%m-%d")
    data_ate = request.args.get("data_ate") or hoje.strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT fornecedor, vencimento, valor, valor_pago, status, categorias, tipo, centro_de_custo, codigo
        FROM contas_a_pagar
        WHERE date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2))
        BETWEEN ? AND ?
    """, (data_de, data_ate))
    registros = cursor.fetchall()

    # Totais
    total_previsto = total_pago = saldo = total_atraso = total_hoje = total_amanha = 0
    hoje = datetime.now().date()
    amanha = hoje + timedelta(days=1)

    for r in registros:
        try:
            vencimento = datetime.strptime(r[1], "%d/%m/%Y").date()
            valor = float(str(r[2]).replace(",", ".") or 0)
            valor_pago = float(str(r[3]).replace(",", ".") or 0)

            total_previsto += valor
            total_pago += valor_pago
            saldo += valor_pago + valor

            if vencimento == hoje:
                total_hoje += abs(valor)
            if vencimento == amanha:
                total_amanha += abs(valor)
            if vencimento < hoje and valor_pago == 0:
                total_atraso += abs(valor)
        except Exception as e:
            print("Erro ao processar linha:", e)
            continue

    # Gráfico de linhas (vazio por enquanto)
    fig_linhas = go.Figure()

    # Gráfico por Categoria
    dados_categoria = {}
    for r in registros:
        try:
            categoria = r[5]
            valor = float(str(r[2]).replace(",", ".") or 0)
            if categoria:
                dados_categoria[categoria] = dados_categoria.get(categoria, 0) + abs(valor)
        except:
            continue
    fig_categoria = go.Figure()
    fig_categoria.add_trace(go.Pie(labels=list(dados_categoria.keys()), values=list(dados_categoria.values())))

    # Gráfico por Status
    dados_status = {}
    for r in registros:
        try:
            status = r[4]
            valor = float(str(r[2]).replace(",", ".") or 0)
            if status:
                dados_status[status] = dados_status.get(status, 0) + abs(valor)
        except:
            continue
    fig_status = go.Figure()
    fig_status.add_trace(go.Pie(labels=list(dados_status.keys()), values=list(dados_status.values())))

    # Gráfico por Dia (Barra)
    dados_dia = defaultdict(float)
    for r in registros:
        try:
            vencimento = r[1]
            valor = float(str(r[2]).replace(",", ".") or 0)
            if vencimento:
                dados_dia[vencimento] += abs(valor)
        except:
            continue
    fig_dia = go.Figure()
    fig_dia.add_trace(go.Bar(x=list(dados_dia.keys()), y=list(dados_dia.values())))

    # Lç por Categoria (para interação)
    lancamentos_por_categoria = {}
    for r in registros:
        try:
            categoria = r[5]
            valor = float(str(r[2]).replace(",", ".") or 0)
            if categoria not in lancamentos_por_categoria:
                lancamentos_por_categoria[categoria] = []
            lancamentos_por_categoria[categoria].append({
                "fornecedor": r[0],
                "vencimento": r[1],
                "valor": f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "status": r[4],
                "tipo": r[6],
                "centro": r[7]
            })

        except:
            continue

    # Converte gráficos
    grafico_linhas_json = json.dumps(fig_linhas, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_categoria_json = json.dumps(fig_categoria, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_status_json = json.dumps(fig_status, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_dia_json = json.dumps(fig_dia, cls=plotly.utils.PlotlyJSONEncoder)


    totais = {
        "previsto": f"{total_previsto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "pago": f"{total_pago:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "saldo": f"{saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "atraso": f"{total_atraso:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "hoje": f"{total_hoje:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "amanha": f"{total_amanha:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    }

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
                           totais=totais,
                           lancamentos_categoria=lancamentos_por_categoria,
                           grafico_centro=grafico_centro  # ✅ agora está corretamente dentro


    )


