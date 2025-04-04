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

    # 🔹 Filtro de datas
    hoje = datetime.today()
    data_de = request.args.get("data_de") or hoje.replace(day=1).strftime("%Y-%m-%d")
    data_ate = request.args.get("data_ate") or hoje.strftime("%Y-%m-%d")

    # 🔹 Consulta com filtro de datas (para registros e gráfico)
    cursor.execute("""
        SELECT fornecedor, vencimento, valor, valor_pago, status, categorias, tipo, centro_de_custo, codigo
        FROM contas_a_pagar
        WHERE date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2))
        BETWEEN ? AND ?
    """, (data_de, data_ate))
    registros = cursor.fetchall()

    # 🔹 Também usaremos os mesmos dados para o gráfico de centro de custo
    dados = registros

    def gerar_grafico_por_centro(dados):
        import math

        agrupado = defaultdict(float)
        for linha in dados:
            try:
                centro = linha[7] if linha[7] else 'Indefinido'
                valor = float(str(linha[2]).replace(",", ".")) if linha[2] else 0
                agrupado[centro] += abs(valor)
            except Exception as e:
                print("Erro ao processar linha:", linha)
                print("Erro:", e)

        categorias = list(agrupado.keys())
        valores = list(agrupado.values())
        max_valor = max(valores) if valores else 1

        tamanhos = [max((v / max_valor * 100), 20) for v in valores]

        total = len(categorias)
        posicoes_x = [math.cos(2 * math.pi * i / total) for i in range(total)]
        posicoes_y = [math.sin(2 * math.pi * i / total) for i in range(total)]

        cores = [
            "#0d6efd", "#6f42c1", "#20c997", "#6610f2", "#5bc0de",
            "#6c757d", "#0dcaf0", "#3f6791", "#375a7f", "#8e44ad"
        ]
        cores_usadas = [cores[i % len(cores)] for i in range(total)]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=posicoes_x,
            y=posicoes_y,
            mode='markers+text',
            marker=dict(
                size=tamanhos,
                color=cores_usadas,
                opacity=0.88,
                line=dict(width=2, color='rgba(255,255,255,0.1)')
            ),
            text=[
                f"<b>{cat}</b><br>R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                for cat, v in zip(categorias, valores)
            ],
            textposition='bottom center',
            hoverinfo='text'
        ))

        # 💫 Fundo estilo céu estrelado via gradiente radial CSS
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )

        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    grafico_centro = gerar_grafico_por_centro(dados)

    # 🔹 Cálculos de totais
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

    # 🔹 Gráfico de linhas (vazio por enquanto)
    fig_linhas = go.Figure()

    # 🔹 Gráfico por Categoria
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

    # 🔹 Gráfico por Status
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

    # 🔹 Gráfico por Dia (Barra)
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

    # 🔹 Lançamentos por Categoria (para modal ao clicar no gráfico)
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

    # 🔹 Converte gráficos para JSON
    grafico_linhas_json = json.dumps(fig_linhas, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_categoria_json = json.dumps(fig_categoria, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_status_json = json.dumps(fig_status, cls=plotly.utils.PlotlyJSONEncoder)
    grafico_dia_json = json.dumps(fig_dia, cls=plotly.utils.PlotlyJSONEncoder)

    # 🔹 Totais formatados
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
                           grafico_centro=grafico_centro
    )
