# server_app.py (Versão 2.0 - com API de Gerenciamento)
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# --- CONFIGURAÇÃO ---
LICENSE_FILE = Path("licenses.json")
# IMPORTANTE: Use uma senha forte e complexa aqui!
SECRET_KEY = "N7$kR!9tQ@3vcastro@gmaLz#8wF6730cb61786681742e2fb^2xH&5pJ*0mD+4r" 
PLAN_DURATIONS = {
    "Mensal": 30, "Trimestral": 90, "Semestral": 180,
    "Anual": 365, "Vitalício": 365 * 99
}

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- FUNÇÕES AUXILIARES ---
def load_licenses_server():
    try:
        if not LICENSE_FILE.exists(): return {}
        with open(LICENSE_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except Exception: return {}

def save_licenses_server(licenses):
    try:
        with open(LICENSE_FILE, 'w', encoding='utf-8') as f: json.dump(licenses, f, indent=4, ensure_ascii=False)
        return True
    except Exception: return False

# --- ROTAS DE CLIENTE (sem mudança) ---
@app.route('/activate', methods=['POST'])
def activate_license():
    data = request.json; key = data.get('license_key'); machine_id = data.get('machine_id')
    if not key or not machine_id: return jsonify({'status': 'error', 'message': 'Chave e Machine ID são obrigatórios.'}), 400
    licenses = load_licenses_server()
    if key not in licenses: return jsonify({'status': 'error', 'message': 'Chave de licença inválida.'}), 400
    license_info = licenses[key]
    if license_info.get('status') == 'active' and license_info.get('machine_id') != machine_id: return jsonify({'status': 'error', 'message': 'Esta chave já está em uso em outro computador.'}), 400
    plan_name = license_info.get("plan", "Mensal"); duration_days = PLAN_DURATIONS.get(plan_name, 30)
    license_info['status'] = 'active'; license_info['machine_id'] = machine_id
    license_info['start_date'] = datetime.now().strftime('%Y-%m-%d')
    license_info['expiration_date'] = (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d')
    if save_licenses_server(licenses):
        profile_data = {"name": license_info.get("customer_name"), "email": license_info.get("customer_email"), "phone": license_info.get("customer_phone"), "license_key": key, "expiration_date": license_info.get("expiration_date")}
        return jsonify({'status': 'success', 'message': 'Licença ativada com sucesso.', 'data': profile_data})
    else: return jsonify({'status': 'error', 'message': 'Erro interno do servidor ao salvar a licença.'}), 500

@app.route('/validate', methods=['POST'])
def validate_license():
    data = request.json; key = data.get('license_key'); machine_id = data.get('machine_id')
    licenses = load_licenses_server()
    if key not in licenses: return jsonify({'status': 'error', 'message': 'Chave de licença inválida.'}), 400
    license_info = licenses[key]
    if license_info.get('status') != 'active' or license_info.get('machine_id') != machine_id: return jsonify({'status': 'error', 'message': 'Licença inválida ou para outro computador.'}), 400
    try:
        exp_date = datetime.strptime(license_info['expiration_date'], '%Y-%m-%d')
        if datetime.now() > exp_date:
            license_info['status'] = 'inactive'; save_licenses_server(licenses)
            return jsonify({'status': 'error', 'message': 'Sua licença expirou.'}), 400
    except (ValueError, TypeError):
         return jsonify({'status': 'error', 'message': 'Formato de data de expiração inválido na licença.'}), 500
    profile_data = {"name": license_info.get("customer_name"), "email": license_info.get("customer_email"), "phone": license_info.get("customer_phone"), "license_key": key, "expiration_date": license_info.get("expiration_date")}
    return jsonify({'status': 'success', 'message': 'Licença válida.', 'data': profile_data})

@app.route('/update_profile', methods=['POST'])
def update_profile():
    data = request.json; key = data.get('license_key')
    if not key: return jsonify({'status': 'error', 'message': 'Chave de licença é obrigatória.'}), 400
    licenses = load_licenses_server()
    if key not in licenses: return jsonify({'status': 'error', 'message': 'Chave de licença inválida.'}), 400
    licenses[key]['customer_name'] = data.get('name', licenses[key].get('customer_name'))
    licenses[key]['customer_email'] = data.get('email', licenses[key].get('customer_email'))
    licenses[key]['customer_phone'] = data.get('phone', licenses[key].get('customer_phone'))
    if save_licenses_server(licenses):
        return jsonify({'status': 'success', 'message': 'Perfil atualizado com sucesso.'})
    else:
        return jsonify({'status': 'error', 'message': 'Erro interno ao salvar o perfil.'}), 500

# --- NOVAS ROTAS DE GERENCIAMENTO ---
@app.route('/get_licenses', methods=['GET'])
def get_licenses():
    if request.headers.get('X-Admin-Secret-Key') != SECRET_KEY:
        return jsonify({'status': 'error', 'message': 'Acesso não autorizado.'}), 403
    licenses = load_licenses_server()
    return jsonify(licenses)

@app.route('/update_licenses', methods=['POST'])
def update_licenses():
    if request.headers.get('X-Admin-Secret-Key') != SECRET_KEY:
        return jsonify({'status': 'error', 'message': 'Acesso não autorizado.'}), 403
    new_licenses_data = request.json
    if save_licenses_server(new_licenses_data):
        return jsonify({'status': 'success', 'message': 'Base de licenças atualizada com sucesso.'})
    else:
        return jsonify({'status': 'error', 'message': 'Erro ao salvar a nova base de licenças.'}), 500
