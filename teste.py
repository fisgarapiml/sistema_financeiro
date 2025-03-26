import sqlite3
import os

# Caminho do banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "grupo_fisgar.db")

# Conecta ao banco
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Busca todos os lançamentos que precisam ser reclassificados
cursor.execute("""
    SELECT codigo, fornecedor, comentario
    FROM contas_a_pagar
""")
lancamentos = cursor.fetchall()

# Regras de categorização
def classificar(fornecedor, comentario):
    texto = f"{fornecedor or ''} {comentario or ''}".lower()

    if any(p in texto for p in ["kikakau", "point chips", "toy", "brinquedo", "mola"]):
        return ("Fornecedor - Produtos", "Variável", "Brinquedos", "Produção")

    elif any(p in texto for p in ["pão", "café", "leite", "cuscuz", "colaboradores"]):
        return ("Alimentação", "Variável", "Café da Manhã", "Interno")

    elif any(p in texto for p in ["vt", "vale transporte", "suellen", "funcionário", "colaborador", "salário"]):
        return ("Colaboradores", "Fixo", "RH", "Colaboradores")

    elif any(p in texto for p in ["energia", "água", "internet", "telefonia"]):
        return ("Infraestrutura", "Fixo", "Geral", "Estrutura Operacional")

    elif any(p in texto for p in ["contador", "contabilidade", "imposto", "darf"]):
        return ("Empresa", "Fixo", "Financeiro", "Administração Geral")

    elif any(p in texto for p in ["aluguel", "aluguel loja", "empréstimo", "parcelamento", "financiamento"]):
        return ("Empresa", "Fixo", "Geral", "Financeiro")

    elif any(p in texto for p in ["consultoria", "marketing", "design", "publicidade"]):
        return ("Estratégia", "Variável", "Geral", "Comunicação")

    else:
        return (None, None, None, None)

# Atualiza os lançamentos
atualizados = 0

for codigo, fornecedor, comentario in lancamentos:
    categoria, tipo_custo, centro_de_custo, plano_de_contas = classificar(fornecedor, comentario)

    if categoria:
        cursor.execute("""
            UPDATE contas_a_pagar
            SET categorias = ?, tipo_custo = ?, centro_de_custo = ?, plano_de_contas = ?
            WHERE codigo = ?
        """, (categoria, tipo_custo, centro_de_custo, plano_de_contas, codigo))
        atualizados += 1

conn.commit()
conn.close()

print(f"✅ Reclassificação concluída. {atualizados} lançamentos atualizados com sucesso.")
