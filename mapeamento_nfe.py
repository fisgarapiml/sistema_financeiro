"""
ARQUIVO DE MAPEAMENTO CÓDIGO FORNECEDOR → CÓDIGO INTERNO
Instruções:
1. Copie este arquivo para a pasta principal do seu projeto (onde está app.py, views.py, etc.)
2. Importe as funções no seu módulo de NF-e (ex: compras.py)
"""

# Dicionário completo de mapeamento (código_fornecedor: codigo_interno)
MAPEAMENTO_COMPLETO = {
    # --- BRINQUEDOS (prefixo G) ---
    "000031": "ANELSG",
    "000004": "APITOJUIZG",
    "000242": "ARANHACOLORIDAG",
    "000140": "AVIAOG",
    "000041": "BOLSINHAG",
    "000016": "CORNETAG",
    "000254": "DENTINHOG",
    "000256": "FORMINHASG",
    "000161": "GIROHELICEG",
    "000177": "IOIOMPG",
    "000017": "MINIIOIOG",
    "000134": "MINIPIAOG",
    "000014": "PULSEIRAG",
    "000146": "RELOGIOG",
    "000198": "RELOGIORETG",
    "000019": "SKATEG",
    "000006": "FORMULA1G",

    # --- BALAS/DOCES (prefixo PC/CX) ---
    "1226102": "BALAMASTUVA",
    "1314731": "BALAMASTAMENDOIM",
    "573429": "CHICLEDANNY",
    "1004007": "PIRLYOGURTE",
    "1054842": "BALAMASTIOGURTE",
    "967846": "BALAGELAZEDINHOS",
    "1085891": "BALAGELMORANGO",
    "1206913": "DOCELEITECHUP",
    "1254211": "PIRLRECHFRUTAS",
    "764292": "CHOCGUARDACHUVA",
    "1051018": "PACOCAROLHA",
    "1117011": "BALAGELTWISTER",
    "1133028": "CHICLERECHMORANGO",
    "1286335": "GOMATUBOGURT",
    "969550": "PIRLLAMPIAO",
    "1054835": "BALAMASTSORTIDOS",
    "1293944": "BALAGELTUBESMORANGO",
    "717588": "PIRLPSICODELICO",
    "928632": "PASTMINISORTIDOS",
    "1133035": "CHICLERECHTUTTIFRUT",
    "1133042": "CHICLERECHUVA",
    "1290844": "CHICLEBUZZYFURIOSOS",
    "1291094": "CHICLEBUZZYLADYBUG",

    # --- ADICIONE NOVOS CÓDIGOS AQUI ---
    # Formato: "COD_FORNECEDOR": "COD_INTERNO",
}


def converter_codigo(cod_fornecedor):
    """ 
    Converte código do fornecedor para código interno.
    Retorna "COD_NAO_ENCONTRADO" se não existir no mapeamento.
    """
    return MAPEAMENTO_COMPLETO.get(cod_fornecedor, "COD_NAO_ENCONTRADO")


def carregar_nfe(xml_path):
    """
    Exemplo de função para processar XML e converter códigos automaticamente.
    Modifique conforme sua estrutura de XML!
    """
    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

        produtos = []
        for item in root.findall('.//ns:det', ns):
            cod_fornecedor = item.findtext('ns:prod/ns:cProd', namespaces=ns)
            descricao = item.findtext('ns:prod/ns:xProd', namespaces=ns)
            qtd = float(item.findtext('ns:prod/ns:qCom', namespaces=ns))

            cod_interno = converter_codigo(cod_fornecedor)

            produtos.append({
                'cod_fornecedor': cod_fornecedor,
                'cod_interno': cod_interno,
                'descricao': descricao,
                'quantidade': qtd
            })

        return produtos

    except Exception as e:
        print(f"Erro ao processar XML: {str(e)}")
        return []


# --- EXEMPLO DE USO ---
if __name__ == "__main__":
    # Simulação: Processar um XML e mostrar a conversão
    xml_exemplo = "caminho/para/sua_nfe.xml"  # Substitua pelo caminho real
    itens_nfe = carregar_nfe(xml_exemplo)

    print("Resultado do processamento:")
    for item in itens_nfe:
        print(
            f"Cód. Fornecedor: {item['cod_fornecedor']} → "
            f"Cód. Interno: {item['cod_interno']} | "
            f"Descrição: {item['descricao']} | "
            f"Qtd: {item['quantidade']}"
        )