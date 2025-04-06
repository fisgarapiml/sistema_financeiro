from flask import Blueprint, send_file
import sqlite3
from datetime import datetime, timedelta
from fpdf import FPDF
import io

relatorios_bp = Blueprint("relatorios", __name__)

@relatorios_bp.route("/gerar-pdf-hoje")
def gerar_pdf_hoje():
    hoje = datetime.today()
    hoje_str = hoje.strftime("%d/%m/%Y")

    conn = sqlite3.connect("grupo_fisgar.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT fornecedor, categorias, valor, vencimento
        FROM contas_a_pagar
        WHERE status IN ('Aberto', 'Pendente', 'Pago Parcialmente')
    """)
    dados = cursor.fetchall()
    conn.close()

    pagamentos_hoje = []
    atrasados = []
    previsao_segunda = []
    total_hoje = 0
    total_atrasado = 0
    total_segunda = 0

    # Detecção de sábado e domingo caso seja sexta-feira
    if hoje.weekday() == 4:  # 4 = sexta-feira
        sabado = hoje + timedelta(days=1)
        domingo = hoje + timedelta(days=2)
        sabado_str = sabado.strftime("%d/%m/%Y")
        domingo_str = domingo.strftime("%d/%m/%Y")
    else:
        sabado_str = domingo_str = None

    for d in dados:
        valor = float(str(d[2]).replace(",", "."))
        venc = d[3]

        if venc == hoje_str:
            pagamentos_hoje.append(d)
            total_hoje += valor
        elif sabado_str and venc == sabado_str:
            previsao_segunda.append(d)
            total_segunda += valor
        elif domingo_str and venc == domingo_str:
            previsao_segunda.append(d)
            total_segunda += valor
        else:
            try:
                venc_data = datetime.strptime(venc, "%d/%m/%Y").date()
                if venc_data < hoje.date():
                    atrasados.append(d)
                    total_atrasado += valor
            except:
                continue

    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 16)
            self.set_text_color(0, 102, 204)
            self.cell(0, 10, "GRUPO FISGAR", ln=True, align="C")
            self.set_font("Arial", "", 12)
            self.set_text_color(0)
            self.cell(0, 8, f"CONTAS A PAGAR - {hoje_str}", ln=True, align="C")
            self.ln(10)

        def tabela_lancamentos(self, titulo, dados, total, cor_fundo):
            self.set_fill_color(*cor_fundo)
            self.set_font("Arial", "B", 12)
            self.cell(0, 8, titulo, ln=True, fill=True)

            self.set_font("Arial", "B", 10)
            self.set_fill_color(230, 230, 230)
            self.cell(75, 8, "Fornecedor", 1, 0, 'C', True)
            self.cell(40, 8, "Categoria", 1, 0, 'C', True)
            self.cell(35, 8, "Valor", 1, 0, 'C', True)
            self.cell(40, 8, "Vencimento", 1, 1, 'C', True)

            self.set_font("Arial", "", 10)
            for linha in dados:
                fornecedor = linha[0]
                categoria = linha[1]
                valor = f"R$ {float(linha[2]):,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                venc = linha[3]

                self.cell(75, 8, fornecedor, 1)
                self.cell(40, 8, categoria, 1)
                self.cell(35, 8, valor, 1, 0, 'R')
                self.cell(40, 8, venc, 1, 1)

            self.set_font("Arial", "B", 10)
            total_fmt = f"R$ {total:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            self.cell(150, 8, "TOTAL:", 1)
            self.cell(40, 8, total_fmt, 1, 1, 'R')
            self.ln(8)

    pdf = PDF()
    pdf.add_page()

    # Tabelas no PDF
    pdf.tabela_lancamentos("PAGAMENTOS DE HOJE", pagamentos_hoje, total_hoje, (210, 235, 255))
    pdf.tabela_lancamentos("LANÇAMENTOS ATRASADOS", atrasados, total_atrasado, (255, 225, 225))

    if previsao_segunda:
        pdf.tabela_lancamentos(
            "PREVISÃO PARA SEGUNDA-FEIRA (valores que vencem no final de semana)",
            previsao_segunda,
            total_segunda,
            (255, 255, 200)
        )

    # Exporta
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"relatorio_contas_{hoje_str}.pdf"
    )
