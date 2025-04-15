# modules/nfe/models.py
from datetime import datetime
from app.py import db  # Alterado para importar do SEU app principal

class Fornecedor(db.Model):
    __tablename__ = 'fornecedores_nfe'  # Nome diferente para não conflitar
    id = db.Column(db.Integer, primary_key=True)
    cnpj = db.Column(db.String(14), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)

class NFe(db.Model):
    __tablename__ = 'nfe'
    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores_nfe.id'))
    chave = db.Column(db.String(44), unique=True, nullable=False)
    numero = db.Column(db.String(20), nullable=False)
    data_emissao = db.Column(db.DateTime, nullable=False)  # Tipo mais genérico
    valor_total = db.Column(db.Float, nullable=False)  # Simplificado

class ItemNFe(db.Model):
    __tablename__ = 'nfe_itens'
    id = db.Column(db.Integer, primary_key=True)
    nfe_id = db.Column(db.Integer, db.ForeignKey('nfe.id'))
    descricao = db.Column(db.String(200), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=False)