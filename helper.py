from os import remove
from subprocess import check_output
from constant import Constant
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from google.cloud import pubsub_v1
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from pdf2docx import Converter

import io
import uuid

AZURE_CONNECTION_STRING = ""
AZURE_CONTAINER_NAME = ""
AZURE_PROJECT = ""
AZURE_TOPIC = ""

def get_container_client():
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
    return container_client

def get_url(id):
    container_client = get_container_client()
    
    blob_client = container_client.get_blob_client(f"{id}/filename.txt")
    if blob_client.exists():
        blob_txt_content = blob_client.download_blob().readall()
        filename = blob_txt_content.decode('utf-8')

        blob_client = container_client.get_blob_client(f"{id}/{filename}")
        if blob_client.exists():
            return blob_client.url
    
    return None

def get_template(id):
    container_client = get_container_client()
    
    blob_client = container_client.get_blob_client(f"src/{id}/filename.txt")
    if blob_client.exists():
        blob_txt_content = blob_client.download_blob().readall()
        filename = blob_txt_content.decode('utf-8')

        blob_client = container_client.get_blob_client(f"src/{id}/{filename}")
        if blob_client.exists():
            # Convert blob to file storage
            file_content = blob_client.download_blob().readall()
            file_stream = io.BytesIO(file_content)
            file_storage = FileStorage(
                stream=file_stream,
                filename=filename,
                content_type=blob_client.get_blob_properties().content_settings.content_type
            )
            return file_storage
        else:
            return None
    
    return None

def save_result(result_id, template):
    container_client = get_container_client()
    converted_file = convert_template(template)

    if type(converted_file) is str:
        return False
    
    filename = secure_filename(converted_file.filename)
    blob_client = container_client.get_blob_client(f"{result_id}/{filename}")
    converted_file = converted_file.stream
    blob_client.upload_blob(converted_file)

    converted_file.close()
    remove(filename)

    bytes_data = f"{filename}".encode()
    blob_txt_client = container_client.get_blob_client(f"{result_id}/filename.txt")
    blob_txt_client.upload_blob(bytes_data)

    return True

def upload_template(file):
    template_id = uuid.uuid4()
    filename = secure_filename(file.filename)

    container_client = get_container_client()
    
    blob_client = container_client.get_blob_client(f"src/{template_id}/{filename}")
    file = file.stream
    blob_client.upload_blob(file)

    bytes_data = f"{filename}".encode()
    blob_txt_client = container_client.get_blob_client(f"src/{template_id}/filename.txt")
    blob_txt_client.upload_blob(bytes_data)

    return template_id

def delete_template(template_id):
    container_client = get_container_client()
    blob_txt_client = container_client.get_blob_client(f"src/{template_id}/filename.txt")
    blob_txt_content = blob_txt_client.download_blob().readall()
    filename = blob_txt_content.decode('utf-8')

    blob_client = container_client.get_blob_client(f"src/{template_id}/{filename}")
    blob_client.delete_blob()
    blob_txt_client.delete_blob()

    return True

def publish_task(template_id):
    result_id = uuid.uuid4()

    publisher = pubsub_v1.PublisherClient.from_service_account_json(GCP_SA)
    topic_path = publisher.topic_path(AZURE_PROJECT, AZURE_TOPIC)

    bytes_data = f"{template_id},{result_id}".encode()
    publisher.publish(topic_path, bytes_data)

    return result_id

def check_progress(id):
    container_client = get_container_client()
    
    blob_client = container_client.get_blob_client(f"{id}/filename.txt")
    if blob_client.exists():
        blob_txt_content = blob_client.download_blob().readall()
        filename = blob_txt_content.decode('utf-8')

        blob_client = container_client.get_blob_client(f"{id}/{filename}")
        if blob_client.exists():
            return Constant.STATUS_COMPLETED
        else:
            return Constant.STATUS_NOT_FOUND
    else:
        return Constant.STATUS_IN_PROGRESS

def convert_template(file):
    extension = file.filename.split('.')[1]
    filename = file.filename.split('.')[0]

    if extension == "docx":
        try:
            file.save(f'{filename}.docx')
            check_output(['libreoffice', '--headless', '--convert-to', 'pdf', f'{filename}.docx'])
            fp = open(f'{filename}.pdf', 'rb')
            pdf = FileStorage(
                stream=fp,
                filename=f'{filename}.pdf',
                content_type=Constant.MIME_TYPE_TEMPLATES[1]
            )
            return pdf
        except Exception as e:
            return str(e)
        finally:
            remove(f'{filename}.docx')
    elif extension == "pdf":
        try:
            file.save(f'{filename}.pdf')
            cv = Converter(f'{filename}.pdf')
            cv.convert(f'{filename}.docx')
            cv.close()
            fp = open(f'{filename}.docx', 'rb')
            docx = FileStorage(
                stream=fp,
                filename=f'{filename}.docx',
                content_type=Constant.MIME_TYPE_TEMPLATES[0]
            )
            return docx
        except Exception as e:
            return str(e)
        finally:
            remove(f'{filename}.pdf')
    else:
        return None

def delete_everything():
    container_client = get_container_client()

    blobList=[*container_client.list_blobs()]
    while len(blobList) > 0:
        first256 = blobList[0:255]
        container_client.delete_blobs(*first256)     # delete_blobs() is faster!
        del blobList[0:255]
    
    return True