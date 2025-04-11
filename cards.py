from flask import Flask
from routes.teste_cards import teste_cards_bp

app = Flask(__name__, template_folder='templates')

# Registra os filtros de template
@app.template_filter('formatar_brl')
def formatar_brl(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(".", ",").replace(",", "X").replace("X", ".")
    except:
        return f"R$ {valor}"

@app.template_filter('formatar_data')
def formatar_data(data_str):
    try:
        return data_str.strftime('%d/%m/%Y') if hasattr(data_str, 'strftime') else data_str
    except:
        return data_str

# Registra o Blueprint
app.register_blueprint(teste_cards_bp)

if __name__ == '__main__':
    app.run(debug=True)