from flask import Blueprint, render_template, request
import sqlite3
from datetime import datetime

contas_a_pagar_bp = Blueprint("contas_a_pagar", __name__)

def formatar_valor(valor):
    try:
        return float(str(valor).replace(",", ".").replace("R$", "").strip())
    except:
        return 0.00

@contas_a_pagar_bp.route("/contas-a-pagar")
def contas_a_pagar():
    status = request.args.get("status", "Todos")
    data_inicio = request.args.get("inicio")
    data_fim = request.args.get("fim")
    hoje = datetime.today()

    if not data_inicio:
        data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
    if not data_fim:
        data_fim = hoje.strftime("%Y-%m-%d")

    conn = sqlite3.connect("grupo_fisgar.db")
    cursor = conn.cursor()

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

        # 🔎 Filtro especial para atrasados
        if status == "atrasados":
            if d[8] in ("Aberto", "Pendente", "Pago Parcialmente") and vencimento_data < hoje.date():
                dados_filtrados.append(d)
            continue

        # 🔎 Filtros padrão
        if data_inicio and vencimento_data < datetime.strptime(data_inicio, "%Y-%m-%d").date():
            continue
        if data_fim and vencimento_data > datetime.strptime(data_fim, "%Y-%m-%d").date():
            continue
        if status != "Todos" and d[8] != status:
            continue

        dados_filtrados.append(d)

    # 📊 Totais com base no filtro
    totais = {
        "total": sum(-formatar_valor(d[6]) for d in dados_filtrados),
        "pagos": sum(formatar_valor(d[6]) for d in dados_filtrados if d[8] == "Pago"),
        "pendentes": sum(-formatar_valor(d[6]) for d in dados_filtrados if d[8] in ("Aberto", "Pendente", "Pago Parcialmente")),
        "hoje": sum(-formatar_valor(d[6]) for d in dados_filtrados if d[5] == hoje.strftime("%d/%m/%Y")),
        "atrasados": sum(-formatar_valor(d[6]) for d in dados_filtrados if
                         d[8] in ("Aberto", "Pendente", "Pago Parcialmente") and
                         datetime.strptime(d[5], "%d/%m/%Y").date() < hoje.date())
    }

    # Lista final de lançamentos
    lista = []
    for d in dados_filtrados:
        lista.append({
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
            "raw_valor": d[6]
        })

    # Tipos únicos extraídos da lista
    tipos_unicos = list({item["tipo"] for item in lista if item.get("tipo")})

    # Renderiza a tela
    return render_template("contas_a_pagar.html",
                           lancamentos=lista,
                           totais=totais,
                           status=status,
                           data_inicio=data_inicio,
                           data_fim=data_fim,
                           hoje=hoje.strftime("%Y-%m-%d"),
                           tipos=tipos_unicos)


from flask import request, redirect, url_for

# ✏️ EDITAR EM MASSA (ainda sem tela, só redirecionamento)
@contas_a_pagar_bp.route("/editar-massa", methods=["POST"])
def editar_massa():
    codigos = request.form.getlist("codigos")
    print("Editar os códigos:", codigos)
    # Futuramente redirecionar para uma tela de edição
    return redirect("/contas-a-pagar")

# 💸 BAIXAR EM MASSA
@contas_a_pagar_bp.route("/baixar-massa", methods=["POST"])
def baixar_massa():
    codigos = request.form.getlist("codigos")
    if codigos:
        conn = sqlite3.connect("grupo_fisgar.db")
        cursor = conn.cursor()
        for codigo in codigos:
            cursor.execute("UPDATE contas_a_pagar SET status = 'Pago', valor_pago = valor WHERE codigo = ?", (codigo,))
        conn.commit()
        conn.close()
    return redirect("/contas-a-pagar")

# 🗑️ EXCLUIR EM MASSA
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
@contas_a_pagar_bp.route("/salvar-edicao-massa", methods=["POST"])
def salvar_edicao_massa():
    codigos = request.form.getlist("codigos")
    conn = sqlite3.connect("grupo_fisgar.db")
    cursor = conn.cursor()

    for codigo in codigos:
        fornecedor = request.form.get(f"fornecedor_{codigo}", "")
        categoria = request.form.get(f"categoria_{codigo}", "")
        plano = request.form.get(f"plano_{codigo}", "")
        centro = request.form.get(f"centro_{codigo}", "")
        valor = request.form.get(f"valor_{codigo}", "0").replace(",", ".")
        status = request.form.get(f"status_{codigo}", "")
        venc = request.form.get(f"vencimento_{codigo}", "")

        # Formatar data para dd/mm/yyyy
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



