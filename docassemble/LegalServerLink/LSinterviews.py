# pre-load
from flask import request, jsonify
from flask_cors import cross_origin
from docassemble.base.util import get_config
from docassemble.webapp.app_object import app, csrf
from docassemble.webapp.server import api_verify, jsonify_with_status

@app.route('/lsinterviews', methods=['GET'])
@csrf.exempt
@cross_origin(origins='*', methods=['GET', 'HEAD'], automatic_options=True)
def ls_interviews():
    if not api_verify(roles=['legalserver']):
        return jsonify_with_status({"url": "Access denied."}, 403)
    interview_data = get_config('legalserver').get('interviews')
    for item in interview_data:
        item.setdefault('external',False)
        
    return jsonify({'interviews': interview_data})
