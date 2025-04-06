import sqlite3

conn = sqlite3.connect("grupo_fisgar.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT codigo, fornecedor, categorias, centro_de_custo, tipo,
           vencimento, valor, valor_pago, status
    FROM contas_a_pagar
    ORDER BY vencimento DESC
    LIMIT 10
""")

dados = cursor.fetchall()
conn.close()

for d in dados:
    print(f"""
    Código: {d[0]}
    Fornecedor: {d[1]}
    Categoria: {d[2]}
    Centro: {d[3]}
    Tipo: {d[4]}
    Vencimento: {d[5]}
    Valor: {d[6]}
    Valor Pago: {d[7]}
    Status: {d[8]}
    """)
