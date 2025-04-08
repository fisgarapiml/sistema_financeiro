import sqlite3

conn = sqlite3.connect("grupo_fisgar - copia.db")
cursor = conn.cursor()

# Verificar os últimos lançamentos que deveriam ter sido baixados
cursor.execute("SELECT codigo, fornecedor, valor, valor_pago, status, vencimento FROM contas_a_pagar ORDER BY codigo DESC LIMIT 10")
for row in cursor.fetchall():
    print(row)

conn.close()
