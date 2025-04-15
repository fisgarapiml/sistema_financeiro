import os
import xml.etree.ElementTree as ET

PASTA_XML = os.path.join('uploads', 'xml')


def extrair_namespace(tag):
    if tag[0] == '{':
        return tag[1:].split('}')[0]
    return ''


def listar_notas_fiscais():
    notas = []

    if not os.path.exists(PASTA_XML):
        os.makedirs(PASTA_XML)

    for arquivo in os.listdir(PASTA_XML):
        if arquivo.endswith(".xml"):
            caminho_arquivo = os.path.join(PASTA_XML, arquivo)
            try:
                tree = ET.parse(caminho_arquivo)
                root = tree.getroot()
                namespace = extrair_namespace(root.tag)
                ns = {'ns': namespace} if namespace else {}

                fornecedor = root.find('.//ns:emit/ns:xNome', ns)
                numero_nfe = root.find('.//ns:ide/ns:nNF', ns)

                produtos = []
                for det in root.findall('.//ns:det', ns):
                    prod = det.find('ns:prod', ns)
                    ipi = det.find('ns:imposto/ns:IPI/ns:IPITrib/ns:pIPI', ns)

                    produto = {
                        'codigo': prod.findtext('ns:cProd', default='', namespaces=ns),
                        'descricao': prod.findtext('ns:xProd', default='', namespaces=ns),
                        'ncm': prod.findtext('ns:NCM', default='', namespaces=ns),
                        'unidade': prod.findtext('ns:uCom', default='', namespaces=ns),
                        'quantidade': prod.findtext('ns:qCom', default='', namespaces=ns),
                        'valor_unitario': prod.findtext('ns:vUnCom', default='', namespaces=ns),
                        'valor_total': prod.findtext('ns:vProd', default='', namespaces=ns),
                        'desconto': prod.findtext('ns:vDesc', default='0.00', namespaces=ns),
                        'ipi': ipi.text if ipi is not None else '0.00'
                    }
                    produtos.append(produto)

                nota = {
                    'arquivo': arquivo,
                    'fornecedor': fornecedor.text if fornecedor is not None else 'Não encontrado',
                    'número_nfe': numero_nfe.text if numero_nfe is not None else 'Não encontrado',
                    'produtos': produtos
                }

                notas.append(nota)

            except ET.ParseError:
                print(f"Erro ao ler o arquivo XML: {arquivo}")

    return notas


if __name__ == '__main__':
    print("Lendo XMLs da pasta...")
    resultados = listar_notas_fiscais()

    for nota in resultados:
        print(f"\nArquivo: {nota['arquivo']}")
        print(f"Fornecedor: {nota['fornecedor']}")
        print(f"Número NF-e: {nota['número_nfe']}")
        print("Produtos:")
        for produto in nota['produtos']:
            print(f" - {produto['descricao']} | Qtd: {produto['quantidade']} | Vlr Unit: {produto['valor_unitario']} | IPI: {produto['ipi']}")
