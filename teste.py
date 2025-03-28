import sqlite3
conn = sqlite3.connect("grupo_fisgar.db")
cursor = conn.cursor()
cursor.execute("SELECT codigo, fornecedor, valor, valor_pago, vencimento FROM contas_a_pagar ORDER BY vencimento")
for row in cursor.fetchall():
    print(row)
conn.close()
