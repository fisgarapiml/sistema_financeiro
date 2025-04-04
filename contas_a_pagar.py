from flask import render_template, request
import sqlite3
import plotly
import math
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
        import random
        import math
        from collections import defaultdict
        import plotly.graph_objs as go
        import plotly

        agrupado = defaultdict(float)
        for linha in dados:
            try:
                centro = linha[8] if linha[8] else 'Indefinido'
                valor = float(linha[2]) if linha[2] else 0
                agrupado[centro] += abs(valor)
            except:
                continue

        centros = list(agrupado.keys())
        valores = list(agrupado.values())
        max_valor = max(valores) if valores else 1

        tamanhos = [max(40, (v / max_valor) * 140) for v in valores]

        cores = ['#00ffff', '#ff69b4', '#ffd700', '#00ff00', '#ff6347', '#1e90ff',
                 '#ff1493', '#32cd32', '#ffa500', '#9932cc', '#00ced1', '#ff4500']
        cores_usadas = [cores[i % len(cores)] for i in range(len(centros))]

        random.seed(42)
        angulo_inicial = random.randint(0, 360)
        distancia_base = 8.0
        x, y = [], []

        for i in range(len(centros)):
            angulo = math.radians(angulo_inicial + i * 90)
            raio = distancia_base + i * 3.5
            x.append(raio * math.cos(angulo))
            y.append(raio * math.sin(angulo))

        customdata = centros

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='markers+text',
            marker=dict(
                size=tamanhos,
                color=cores_usadas,
                opacity=0.95,
                line=dict(color='white', width=2)
            ),
            text=[
                f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                for v in valores
            ],
            textposition='bottom center',
            textfont=dict(color='white', size=10),
            hoverinfo='text',
            customdata=customdata,
            hovertemplate="%{text}<br>Centro: %{customdata}<extra></extra>"
        ))

        fig.update_layout(
            title={
                'text': "🌌 Total por Centro de Custo",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 22, 'color': 'white'}
            },
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(t=100, b=160, l=40, r=40),
            height=660,
            showlegend=False,
            clickmode='event+select'
        )

        fig.update_traces(
            hoverlabel=dict(bgcolor="black", font_size=13, font_color="white"),
            hoverinfo="skip",
            selected=dict(marker=dict(opacity=1)),
            unselected=dict(marker=dict(opacity=0.2))
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

    def gerar_grafico_por_categoria(dados):
        import random
        import math
        from collections import defaultdict
        import plotly.graph_objs as go
        import plotly

        agrupado = defaultdict(float)
        for linha in dados:
            try:
                categoria = linha[5] if linha[5] else 'Indefinido'
                valor = float(str(linha[2]).replace(",", ".") or 0)
                agrupado[categoria] += abs(valor)
            except:
                continue

        categorias = list(agrupado.keys())
        valores = list(agrupado.values())
        max_valor = max(valores) if valores else 1

        tamanhos = [max(40, (v / max_valor) * 140) for v in valores]

        cores = ['#00ffff', '#ff69b4', '#ffd700', '#00ff00', '#ff6347', '#1e90ff',
                 '#ff1493', '#32cd32', '#ffa500', '#9932cc', '#00ced1', '#ff4500']
        cores_usadas = [cores[i % len(cores)] for i in range(len(categorias))]

        random.seed(42)
        angulo_inicial = random.randint(0, 360)
        x, y = [], []

        for i in range(len(categorias)):
            angulo = math.radians(angulo_inicial + i * 137.5)
            raio = 25.5 + i * 50
            x.append((raio * math.cos(angulo)) + 20)
            y.append((raio * math.sin(angulo)) - 40)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='markers+text',
            marker=dict(
                size=tamanhos,
                color=cores_usadas,
                opacity=0.95,
                line=dict(color='white', width=2)
            ),
            text=[
                f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                for v in valores
            ],
            textposition='bottom center',
            textfont=dict(color='white', size=10),
            hoverinfo='text',
            customdata=categorias,
            hovertemplate="%{text}<br>Categoria: %{customdata}<extra></extra>"
        ))

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(visible=False, range=[-450, 450]),
            yaxis=dict(visible=False, range=[-450, 450]),
            margin=dict(t=40, b=40, l=40, r=40),
            height=500,
            width=500,
            showlegend=False,
            clickmode='event+select'
        )

        fig.update_traces(
            hoverlabel=dict(bgcolor="black", font_size=13, font_color="white"),
            hoverinfo="skip",
            selected=dict(marker=dict(opacity=1)),
            unselected=dict(marker=dict(opacity=0.2))
        )

        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


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
    grafico_categoria_json = gerar_grafico_por_categoria(dados)
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
