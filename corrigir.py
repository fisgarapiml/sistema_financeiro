import sqlite3
import os

# Caminho do banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "grupo_fisgar.db")

print(f"📁 Usando banco de dados: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT codigo, fornecedor, comentario FROM contas_a_pagar")
registros = cursor.fetchall()

# Nova função de classificação com base nos fornecedores reais
def classificar(texto):
    texto = texto.lower()

    if any(p in texto for p in ["mercado livre", "mercado pago", "ebazar.com.br"]):
        return ("Plataforma", "Variável", "Vendas", "Intermediação Online")

    elif any(p in texto for p in ["livraria fontes", "apostila", "caderno", "material didático"]):
        return ("Materiais Educativos", "Variável", "Escritório", "Treinamento/Estudo")

    elif "reembolso" in texto:
        return ("Reembolso", "Variável", "Financeiro", "Reembolsos")

    elif "cartão mercado pago" in texto:
        return ("Cartões", "Variável", "Financeiro", "Cartão Empresarial")

    elif any(p in texto for p in ["wa transportes", "frete de fornecedor"]):
        return ("Logística", "Variável", "Entregas", "Frete Flex")

    elif "simples nacional" in texto:
        return ("Impostos", "Fixo", "Fiscal", "Tributos Federais")

    elif "grupofisgar" in texto:
        return ("Transferência Interna", "Fixo", "Holding", "Financeiro")

    elif "ki-kakau" in texto:
        return ("Fornecedor - Produtos", "Variável", "Produtos", "Produção")

    elif any(p in texto for p in ["altamiris", "leticia", "felipe", "yasmin", "yasmim", "julia", "nadia", "simone", "elismar", "diarista"]):
        return ("Colaboradores", "Fixo", "RH", "Pagamento Terceiros")

    elif any(p in texto for p in ["restaurante", "alimentação"]):
        return ("Alimentação", "Variável", "RH", "Refeição")

    return (None, None, None, None)

# Atualiza os registros
atualizados = 0
for codigo, fornecedor, comentario in registros:
    texto = f"{fornecedor or ''} {comentario or ''}"
    nova_categoria, novo_tipo, novo_ccusto, novo_plano = classificar(texto)

    if nova_categoria:
        cursor.execute("""
            UPDATE contas_a_pagar
            SET categorias = ?, tipo_custo = ?, centro_de_custo = ?, plano_de_contas = ?
            WHERE codigo = ?
        """, (nova_categoria, novo_tipo, novo_ccusto, novo_plano, codigo))
        atualizados += 1
        if atualizados <= 5:
            print(f"✔️ {codigo} → {nova_categoria} / {novo_plano}")

conn.commit()

print(f"\n✅ Reclassificação concluída com sucesso: {atualizados} registros atualizados.")
# Correção final de valores do plano_de_contas baseado em termos exatos
cursor.execute("SELECT codigo, plano_de_contas FROM contas_a_pagar WHERE plano_de_contas IN (?, ?, ?, ?)", (
    "Caixa",
    "Ensumos = Embalagens Fitas ETC...",
    "Escritório",
    "Produtos de Limpeza ou manutenção"
))
registros_finais = cursor.fetchall()
corrigidos = 0

for codigo, plano in registros_finais:
    if plano == "Caixa" or plano == "Ensumos = Embalagens Fitas ETC...":
        novo_plano = "Insumos - Embalagens"
        categoria = "Produção"
        tipo = "Variável"
        centro = "Embalagens"

    elif plano == "Escritório":
        novo_plano = "Escritório"
        categoria = "Infraestrutura"
        tipo = "Fixo"
        centro = "Administrativo"

    elif plano == "Produtos de Limpeza ou manutenção":
        novo_plano = "Manutenção Geral"
        categoria = "Manutenção"
        tipo = "Variável"
        centro = "Higienização"

    else:
        continue

    cursor.execute("""
        UPDATE contas_a_pagar
        SET plano_de_contas = ?, categorias = ?, tipo_custo = ?, centro_de_custo = ?
        WHERE codigo = ?
    """, (novo_plano, categoria, tipo, centro, codigo))
    corrigidos += 1
    print(f"🔧 Corrigido código {codigo} → {novo_plano}")

conn.commit()
print(f"\n✅ Correções finais aplicadas: {corrigidos}")
conn.close()

