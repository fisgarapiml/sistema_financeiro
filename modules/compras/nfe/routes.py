from flask import Blueprint, render_template, request
from modules.nfe.models import NFe

nfe_blueprint = Blueprint('nfe', __name__, url_prefix='/nfe')

@nfe_blueprint.route('/importar', methods=['GET', 'POST'])
def importar_nfe():
    if request.method == 'POST':
        arquivo = request.files['arquivo']
        arquivo.save(f"uploads/nfe/{arquivo.filename}")
        return "Arquivo enviado para processamento!"
    return render_template('nfe/importar.html')

@nfe_blueprint.route('/listar')
def listar_nfe():
    nfes = NFe.query.order_by(NFe.data_emissao.desc()).limit(50).all()
    return render_template('nfe/listar.html', nfes=nfes)