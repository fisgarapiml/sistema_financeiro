from flask import Blueprint, render_template, request, flash
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from werkzeug.utils import secure_filename

compras_bp = Blueprint('compras', __name__, template_folder='../templates')

# Configurações
UPLOAD_FOLDER = os.path.join('uploads', 'xml')
ALLOWED_EXTENSIONS = {'xml'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_xml(xml_path):
    """Parseia o XML e retorna dados estruturados"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

        # Dados da NF-e
        nfe_data = {
            'numero': root.findtext('.//ns:nNF', namespaces=ns),
            'chave': root.find('.//ns:infNFe', ns).attrib['Id'][3:],
            'data_emissao': root.findtext('.//ns:dEmi', namespaces=ns),
            'fornecedor': {
                'nome': root.findtext('.//ns:emit/ns:xNome', namespaces=ns),
                'cnpj': root.findtext('.//ns:emit/ns:CNPJ', namespaces=ns)
            }
        }

        # Processa itens
        produtos = []
        for det in root.findall('.//ns:det', ns):
            prod = det.find('ns:prod', ns)
            ipi = det.find('ns:imposto/ns:IPI/ns:IPITrib/ns:pIPI', ns)

            descricao = prod.findtext('ns:xProd', '', namespaces=ns)
            valor_unitario = float(prod.findtext('ns:vUnCom', '0', namespaces=ns))
            ipi_valor = float(ipi.text) if ipi is not None else 0.0

            # Extrai quantidades da descrição
            embalagem_info = extrair_quantidades(descricao)

            produtos.append({
                'codigo': prod.findtext('ns:cProd', '', namespaces=ns),
                'descricao': descricao,
                'unidade': prod.findtext('ns:uCom', '', namespaces=ns),
                'quantidade': float(prod.findtext('ns:qCom', '0', namespaces=ns)),
                'valor_unitario': valor_unitario,
                'ipi': ipi_valor,
                **embalagem_info,
                'custo_unit_real': calcular_custo(valor_unitario, embalagem_info)
            })

        return {'nfe': nfe_data, 'produtos': produtos}

    except Exception as e:
        raise ValueError(f"Erro ao processar XML: {str(e)}")


def extrair_quantidades(descricao):
    """Extrai informações de embalagem da descrição do produto"""
    # Padrões comuns: "CX C/ 50 UN", "PACOTE C/ 100", "10 X 50UN"
    padrao = re.compile(
        r'(?P<qtd_embalagem>\d+)\s*(X|\/|C\/)?\s*(?P<qtd_unidade>\d+)?\s*(CX|PC|UN|PCT|FD|MIL|DP)?',
        re.IGNORECASE
    )

    match = padrao.search(descricao.upper())
    if match:
        qtd_embalagem = int(match.group('qtd_embalagem')) if match.group('qtd_embalagem') else 1
        qtd_unidade = int(match.group('qtd_unidade')) if match.group('qtd_unidade') else 1
    else:
        qtd_embalagem = qtd_unidade = 1

    return {
        'qtd_embalagem': qtd_embalagem,
        'qtd_unidade': qtd_unidade
    }


def calcular_custo(valor_unitario, embalagem_info):
    """Calcula o custo unitário real"""
    try:
        return valor_unitario / (embalagem_info['qtd_embalagem'] * embalagem_info['qtd_unidade'])
    except ZeroDivisionError:
        return 0.0


@compras_bp.route("/compras/edicao-nfe", methods=['GET', 'POST'])
def edicao_nfe():
    if request.method == 'POST':
        # Processar upload de arquivo
        if 'nfe_file' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return render_template("compras/edicao_nfe.html")

        file = request.files['nfe_file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado', 'error')
            return render_template("compras/edicao_nfe.html")

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            try:
                data = parse_xml(filepath)
                return render_template("compras/edicao_nfe.html", **data)
            except ValueError as e:
                flash(str(e), 'error')

    # GET ou falha no POST
    return render_template("compras/edicao_nfe.html")