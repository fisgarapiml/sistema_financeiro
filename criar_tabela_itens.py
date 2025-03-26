import sqlite3

# Caminho do banco
conn = sqlite3.connect("grupo_fisgar.db")
cursor = conn.cursor()

# Criar tabela itens_da_compra
cursor.execute("""
CREATE TABLE IF NOT EXISTS itens_da_compra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_lancamento INTEGER,
    produto TEXT,
    unidade TEXT,
    quantidade REAL,
    valor_unitario REAL,
    valor_total REAL,
    data_insercao TEXT
)
""")

conn.commit()
conn.close()
print("✅ Tabela 'itens_da_compra' criada com sucesso.")
