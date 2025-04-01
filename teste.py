import sqlite3

def garantir_colunas(banco, tabela, colunas):
    conn = sqlite3.connect(banco)
    cursor = conn.cursor()

    # Recuperar colunas existentes
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas_existentes = [info[1] for info in cursor.fetchall()]

    for coluna, tipo in colunas.items():
        if coluna not in colunas_existentes:
            try:
                cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
                print(f"✅ Coluna '{coluna}' criada com sucesso.")
            except Exception as e:
                print(f"❌ Erro ao criar a coluna '{coluna}': {e}")
        else:
            print(f"✔️ Coluna '{coluna}' já existe.")

    conn.commit()
    conn.close()

# 🧱 Colunas essenciais do projeto (com tipos)
colunas_necessarias = {
    "tipo": "TEXT",
    "centro_de_custo": "TEXT",
    "categorias": "TEXT",
    "tipo_custo": "TEXT"
}

# 🚀 Executar
if __name__ == "__main__":
    garantir_colunas("grupo_fisgar.db", "contas_a_pagar", colunas_necessarias)
