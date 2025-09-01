import os
from flask import render_template, request, jsonify, send_from_directory, abort
from docx import Document
from PyPDF2 import PdfReader
from flask import Blueprint, current_app

# Criando o blueprint de "documentos"
documentos_bp = Blueprint("documentos", __name__, template_folder="../templates")

DOCUMENTOS_FOLDER = os.path.join('static', 'documentos')
os.makedirs(DOCUMENTOS_FOLDER, exist_ok=True)

# -------------------- documentos --------------------
@documentos_bp.route("/documentos")
def documentos():
    arquivos = os.listdir(DOCUMENTOS_FOLDER)
    arquivos = [{"arquivo": f} for f in arquivos if os.path.isfile(os.path.join(DOCUMENTOS_FOLDER, f))]
    return render_template("documentos.html", arquivos=arquivos)

@documentos_bp.route("/documentos/api", methods=["POST"])
def documentos_api():
    termo = request.json.get("termo", "").strip()
    resultados = []

    # 👉 Se não tiver termo, retorna todos os arquivos
    if not termo:
        arquivos = os.listdir(DOCUMENTOS_FOLDER)
        resultados = [{"arquivo": f} for f in arquivos if os.path.isfile(os.path.join(DOCUMENTOS_FOLDER, f))]
    else:
        resultados = buscar_nos_documentos(DOCUMENTOS_FOLDER, termo)

    return jsonify(resultados)

@documentos_bp.route("/documentos/download/<path:filename>")
def download_documento(filename):
    """Permite download seguro de arquivos dentro de static/documentos"""
    try:
        return send_from_directory(DOCUMENTOS_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)

# -------------------- Função de busca --------------------
def buscar_nos_documentos(pasta, termo):
    resultados = []
    termo = termo.lower()

    for root, _, files in os.walk(pasta):
        for file in files:
            caminho = os.path.join(root, file)

            # 1. Busca no nome do arquivo
            if termo in file.lower():
                resultados.append({"arquivo": file})
                continue

            # 2. Busca dentro de DOCX
            if file.lower().endswith(".docx"):
                try:
                    doc = Document(caminho)
                    if any(termo in par.text.lower() for par in doc.paragraphs):
                        resultados.append({"arquivo": file})
                except Exception as e:
                    print(f"Erro ao ler DOCX {file}: {e}")

            # 3. Busca dentro de PDF
            elif file.lower().endswith(".pdf"):
                try:
                    reader = PdfReader(caminho)
                    for page in reader.pages:
                        texto = page.extract_text() or ""
                        if termo in texto.lower():
                            resultados.append({"arquivo": file})
                            break
                except Exception as e:
                    print(f"Erro ao ler PDF {file}: {e}")

    return resultados
