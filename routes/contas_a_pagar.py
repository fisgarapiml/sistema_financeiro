from flask import Blueprint, render_template, request, redirect, jsonify
from datetime import datetime
import sqlite3

contas_a_pagar_bp = Blueprint("contas_a_pagar", __name__)


def formatar_valor(valor):
    try:
        return float(str(valor).replace(",", ".").replace("R$", "").strip())
    except:
        return 0.00


@contas_a_pagar_bp.route("/contas-a-pagar")
def contas_a_pagar():
    try:
        status = request.args.get("status", "Todos")
        from calendar import monthrange

        hoje = datetime.today()
        mes_atual = hoje.month
        ano_atual = hoje.year

        data_inicio = request.args.get("inicio") or f"{ano_atual}-{mes_atual:02d}-01"
        data_fim = request.args.get("fim") or f"{ano_atual}-{mes_atual:02d}-{monthrange(ano_atual, mes_atual)[1]}"

        formato_json = request.args.get("json") == "1"
        hoje = datetime.today()
        data_hoje_str = hoje.strftime("%d/%m/%Y")

        # Conexão com o banco
        conn = sqlite3.connect("grupo_fisgar.db")
        cursor = conn.cursor()

        # 🔍 Cálculo separado para o card "Atrasados" (valor real direto do banco)
        cursor.execute("""
            SELECT valor
            FROM contas_a_pagar
            WHERE status IN ('Aberto', 'Pendente', 'Pago Parcialmente')
              AND vencimento < ?
        """, (data_hoje_str,))
        valores_atrasados = [formatar_valor(row[0]) for row in cursor.fetchall()]
        total_atrasado = -sum(valores_atrasados)

        # Consulta para JSON (lançamentos do dia)
        if formato_json and status == "hoje":
            try:
                cursor.execute("""
                    SELECT codigo, fornecedor, categorias, centro_de_custo, tipo,
                           vencimento, valor, valor_pago, status, plano_de_contas
                    FROM contas_a_pagar
                    WHERE vencimento = ? AND status != 'Pago'
                """, (data_hoje_str,))

                dados = cursor.fetchall()
                conn.close()

                if not dados:
                    return jsonify({
                        "lancamentos": [],
                        "total": 0,
                        "message": "Nenhum lançamento encontrado para hoje"
                    })

                lancamentos = [{
                    "codigo": d[0],
                    "fornecedor": d[1],
                    "categoria": d[2],
                    "valor": f"R$ {formatar_valor(d[6]):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "status": d[8],
                    "vencimento": d[5]
                } for d in dados]

                return jsonify({
                    "lancamentos": lancamentos,
                    "total": sum(formatar_valor(d[6]) for d in dados)
                })

            except Exception as e:
                conn.close()
                return jsonify({
                    "error": "Erro ao consultar lançamentos",
                    "details": str(e)
                }), 500

        # Consulta normal para HTML
        try:
            cursor.execute("""
                SELECT codigo, fornecedor, categorias, centro_de_custo, tipo,
                       vencimento, valor, valor_pago, status, plano_de_contas
                FROM contas_a_pagar
            """)
            dados = cursor.fetchall()
            conn.close()

            # Filtragem dos dados
            dados_filtrados = []
            for d in dados:
                try:
                    vencimento = datetime.strptime(d[5].strip(), "%d/%m/%Y").date()
                except:
                    continue

                if status == "atrasados":
                    if d[8] not in ("Aberto", "Pendente", "Pago Parcialmente") or vencimento >= hoje.date():
                        continue

                if data_inicio and vencimento < datetime.strptime(data_inicio, "%Y-%m-%d").date():
                    continue
                if data_fim and vencimento > datetime.strptime(data_fim, "%Y-%m-%d").date():
                    continue
                if status != "Todos" and status != "atrasados" and d[8] != status:
                    continue

                dados_filtrados.append(d)

            # Cálculo de totais

            totais = {
                "total": sum(-formatar_valor(d[6]) for d in dados_filtrados),
                "pagos": sum(formatar_valor(d[6]) for d in dados_filtrados if d[8] == "Pago"),
                "pendentes": sum(-formatar_valor(d[6]) for d in dados_filtrados if
                                 d[8] in ("Aberto", "Pendente", "Pago Parcialmente")),
                "hoje": sum(-formatar_valor(d[6]) for d in dados_filtrados
                            if datetime.strptime(d[5], "%d/%m/%Y").date() == hoje.date()),
                "atrasados": sum(-formatar_valor(d[6]) for d in dados_filtrados
                                 if d[8] in ("Aberto", "Pendente", "Pago Parcialmente") and
                                 datetime.strptime(d[5], "%d/%m/%Y").date() < hoje.date())
            }

            # Preparação dos dados para o template
            lista = [{
                "codigo": d[0],
                "fornecedor": d[1],
                "categoria": d[2],
                "centro": d[3],
                "tipo": d[4],
                "vencimento": d[5],
                "valor": f"R$ {formatar_valor(d[6]):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "valor_pago": f"R$ {formatar_valor(d[7]):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "status": d[8],
                "plano": d[9],
                "raw_valor": formatar_valor(d[6])
            } for d in dados_filtrados]

            tipos_unicos = list({item["tipo"] for item in lista if item.get("tipo")})

            return render_template(
                "contas_a_pagar.html",
                lancamentos=lista,
                totais=totais,
                status=status,
                data_inicio=data_inicio,
                data_fim=data_fim,
                hoje=hoje.strftime("%Y-%m-%d"),
                tipos=tipos_unicos
            )

        except Exception as e:
            conn.close()
            return render_template(
                "contas_a_pagar.html",
                error_message=f"Erro ao carregar dados: {str(e)}"
            )

    except Exception as e:
        return jsonify({
            "error": "Erro interno no servidor",
            "details": str(e)
        }), 500

@contas_a_pagar_bp.route("/salvar-edicao-massa", methods=["POST"])
def salvar_edicao_massa():
    codigos = request.form.getlist("codigos")
    conn = sqlite3.connect("grupo_fisgar.db")  # Ou "grupo_fisgar - copia.db"
    cursor = conn.cursor()

    for codigo in codigos:
        fornecedor = request.form.get(f"fornecedor_{codigo}", "")
        categoria = request.form.get(f"categoria_{codigo}", "")
        plano = request.form.get(f"plano_{codigo}", "")
        centro = request.form.get(f"centro_{codigo}", "")
        valor = request.form.get(f"valor_{codigo}", "0").replace(",", ".")
        status = request.form.get(f"status_{codigo}", "")
        venc = request.form.get(f"vencimento_{codigo}", "")

        if venc:
            partes = venc.split("-")
            venc = f"{partes[2]}/{partes[1]}/{partes[0]}"

        cursor.execute("""
            UPDATE contas_a_pagar
            SET fornecedor = ?, categorias = ?, plano_de_contas = ?, centro_de_custo = ?,
                valor = ?, status = ?, vencimento = ?
            WHERE codigo = ?
        """, (fornecedor, categoria, plano, centro, valor, status, venc, codigo))

    conn.commit()
    conn.close()
    return redirect("/contas-a-pagar")


# 💸 Salvar baixa em massa
@contas_a_pagar_bp.route("/salvar-baixa-massa", methods=["POST"])
def salvar_baixa_massa():
    codigos_raw = request.form.get("codigos", "")
    data_pagamento = request.form.get("dataPagamento")
    opcao_valor = request.form.get("opcaoValor")
    valor_informado = request.form.get("valorInformado")

    if not codigos_raw or not data_pagamento:
        return redirect("/contas-a-pagar")

    codigos = codigos_raw.split(",")

    conn = sqlite3.connect("grupo_fisgar.db")
    cursor = conn.cursor()

    for codigo in codigos:
        if opcao_valor == "diferente" and valor_informado:
            try:
                valor_convertido = float(valor_informado.replace(",", "."))
            except:
                valor_convertido = 0
            cursor.execute("""
                UPDATE contas_a_pagar
                SET status = 'Pago',
                    valor_pago = ?,
                    vencimento = ?
                WHERE codigo = ?
            """, (valor_convertido, data_pagamento, codigo))
        else:
            cursor.execute("""
                UPDATE contas_a_pagar
                SET status = 'Pago',
                    valor_pago = valor,
                    vencimento = ?
                WHERE codigo = ?
            """, (data_pagamento, codigo))

    conn.commit()
    conn.close()
    return redirect("/contas-a-pagar")

# 🗑️ Excluir em massa
@contas_a_pagar_bp.route("/excluir-massa", methods=["POST"])
def excluir_massa():
    codigos = request.form.getlist("codigos")
    if codigos:
        conn = sqlite3.connect("grupo_fisgar.db")
        cursor = conn.cursor()
        cursor.executemany("DELETE FROM contas_a_pagar WHERE codigo = ?", [(c,) for c in codigos])
        conn.commit()
        conn.close()
    return redirect("/contas-a-pagar")


@contas_a_pagar_bp.route("/buscar-lancamento")
def buscar_lancamento():
    codigo = request.args.get("codigo")
    conn = sqlite3.connect("grupo_fisgar.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM contas_a_pagar WHERE codigo = ?", (codigo,))
    dados = cursor.fetchone()
    conn.close()

    return jsonify({
        "codigo": dados[0],
        "fornecedor": dados[1],
        "valor": dados[6]
    })

