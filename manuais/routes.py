import os
from flask import render_template, request, jsonify, send_from_directory, abort
from docx import Document
from PyPDF2 import PdfReader
from flask import Blueprint

# Criando o blueprint de "manuais"
manuais_bp = Blueprint("manuais", __name__, template_folder="../templates")

MANUAIS_FOLDER = os.path.join('static', 'manuais')
os.makedirs(MANUAIS_FOLDER, exist_ok=True)

# -------------------- Manuais --------------------
@manuais_bp.route("/manuais")
def manuais():
    arquivos = os.listdir(MANUAIS_FOLDER)
    arquivos = [{"arquivo": f} for f in arquivos if os.path.isfile(os.path.join(MANUAIS_FOLDER, f))]
    return render_template("manuais.html", arquivos=arquivos)

@manuais_bp.route("/manuais/api", methods=["POST"])
def manuais_api():
    termo = request.json.get("termo", "").strip()
    resultados = []

    # 👉 Se não tiver termo, retorna todos os arquivos
    if not termo:
        arquivos = os.listdir(MANUAIS_FOLDER)
        resultados = [{"arquivo": f} for f in arquivos if os.path.isfile(os.path.join(MANUAIS_FOLDER, f))]
    else:
        resultados = buscar_nos_manuais(MANUAIS_FOLDER, termo)

    return jsonify(resultados)

@manuais_bp.route("/manuais/download/<path:filename>")
def download_manual(filename):
    """Permite download seguro de arquivos dentro de static/manuais"""
    try:
        return send_from_directory(MANUAIS_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)

# -------------------- Função de busca --------------------
def buscar_nos_manuais(pasta, termo):
    resultados = []
    termo = termo.lower()

    for root, _, files in os.walk(pasta):
        for file in files:
            caminho = os.path.join(root, file)

            # 1. Busca no nome
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
