from flask import Flask, redirect
from routes.lancamentos import lancamentos_bp
from routes.contas_a_pagar import contas_a_pagar_bp
from routes.relatorios import relatorios_bp

app = Flask(__name__)

# 🔗 Registro dos blueprints em uso
app.register_blueprint(lancamentos_bp)
app.register_blueprint(contas_a_pagar_bp)
app.register_blueprint(relatorios_bp)


# 🔧 Filtro de formatação de valores
@app.template_filter("formatar")
def formatar(valor):
    try:
        valor = float(str(valor).replace(",", ".").replace("R$", "").strip())
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return "R$ 0,00"

# 📍 Redireciona para a tela principal
@app.route("/")
def home():
    return redirect("/lancamentos")

if __name__ == "__main__":
    app.run(debug=True)
