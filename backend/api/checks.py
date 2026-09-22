from flask import Blueprint, current_app, jsonify, request

blueprint = Blueprint('checks', __name__)


@blueprint.route('/api/check', methods=['GET', 'POST'])
def check():
    deps = current_app.extensions['dependencies']
    status = deps.runner.submit(is_test=request.args.get('test') == 'true')
    return jsonify({'status': status}), 202 if status == 'queued' else 200


@blueprint.get('/api/health')
def health():
    return jsonify({'status': 'healthy'})
