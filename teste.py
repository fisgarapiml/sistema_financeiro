# database.py (ou similar)
import sqlite3
from datetime import datetime


def criar_tabelas_estoque():
    conn = sqlite3.connect('grupo_fisgar.db')
    cursor = conn.cursor()

    # Tabela de Produtos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nome TEXT NOT NULL,
        descricao TEXT,
        categoria TEXT,
        unidade_medida TEXT,
        estoque_minimo INTEGER,
        estoque_atual INTEGER DEFAULT 0,
        fornecedor_id INTEGER,
        data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id)
    )
    ''')

    # Tabela de Fornecedores (se já não existir)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fornecedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cnpj TEXT UNIQUE,
        telefone TEXT,
        email TEXT
    )
    ''')

    # Tabela de Movimentações
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS movimentacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        tipo TEXT NOT NULL, -- 'entrada' ou 'saida'
        quantidade INTEGER NOT NULL,
        valor_unitario REAL,
        documento TEXT,
        data TEXT NOT NULL,
        usuario_id INTEGER,
        FOREIGN KEY (produto_id) REFERENCES produtos(id)
    )
    ''')

    conn.commit()
    conn.close()


# Chamar a função para criar as tabelas
criar_tabelas_estoque()