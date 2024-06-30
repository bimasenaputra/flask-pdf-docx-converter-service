import base64
from constant import Constant
from helper import upload_template, publish_task, check_progress, get_url, delete_everything, get_template, get_template, save_result, delete_template
from flask import Flask, request

import csv
import io
import json

app = Flask(__name__)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)

@app.route("/", methods=["GET"])
def home():
    return '''
        <!doctype html>
        <title>Upload new File to convert (.docx or .pdf)</title>
        <h1>Upload new File</h1>
        <form action="/generate-simple" method=post enctype=multipart/form-data>
        <input type=file name=file>
        <input type=submit value=Upload>
        </form>
        '''

@app.route("/generate-result", methods=["POST"])
def generate_result():
    data_request = request.get_json().get("message").get("data")
    template_id, result_id = base64.b64decode(data_request).decode().split(",")
    if not data_request:
        return {"message": "Data is not valid"}, 400
        
    template = get_template(template_id)
    if not template:
        return {"message": "Template is not found"}, 404
    
    success = save_result(result_id, template)
    delete_template(template_id)

    data = {"result_id": result_id}
    return {"data": data}, 200

@app.route("/generate-bulk", methods=["POST"])
def generate_bulk():
    files = request.files.getlist('file')

    if not files:
        return {"message": "No files uploaded"}, 400

    responses = []
    for file in files:
        if not file or file.mimetype not in Constant.MIME_TYPE_TEMPLATES:
            responses.append({"message": "Template file is not valid"})
    
        template_id = upload_template(file)
        result_id = publish_task(template_id)
        data = {"result_id": result_id}
        responses.append(data)
    
    return {"data": responses}, 202

@app.route("/generate-simple", methods=["POST"])
def generate_simple():
    file = request.files.get("file")
    if not file or file.mimetype not in Constant.MIME_TYPE_TEMPLATES:
        return {"message": "Template file is not valid"}, 400

    template_id = upload_template(file)
    result_id = publish_task(template_id)

    data = {"result_id": result_id}
    return {"data": data}, 202

@app.route("/<uuid:result_id>", methods=["GET"])
def check_status(result_id):
    status = check_progress(result_id)

    if status == Constant.STATUS_NOT_FOUND:
        return {"message": "Result id is not valid"}, 404

    data = {"result_id": result_id, "status": status}
    if status == Constant.STATUS_COMPLETED:
        data["result_url"] = f"{request.base_url}/result"

    return {"data": data}, 200

@app.route("/<uuid:result_id>/result", methods=["GET"])
def get_result(result_id):
    result = get_url(result_id)
    if not result:
         return {"message": "Result id is not valid"}, 404
    
    return result

@app.route("/reset", methods=["GET"])
def delete_all():
    delete_everything()
    return {"message": "Finished"}