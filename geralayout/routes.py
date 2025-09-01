import os
import re
import zipfile
from io import BytesIO
from flask import render_template, request, send_from_directory, redirect, url_for, session, flash, send_file, current_app
import pandas as pd
from flask import Blueprint

# -------------------- Gerar Layout Apdata --------------------

# Criando o blueprint de "geralayout"

geralayout_bp = Blueprint("geralayout", __name__, template_folder="../templates")

# Pastas

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg'}

# -------------------- Funções auxiliares --------------------
def verificar_arquivo(path):
    if not os.path.exists(path):
        flash("Arquivo não encontrado. Faça o upload novamente.", "danger")
        return False
    try:
        with open(path, "rb"):
            pass
    except PermissionError:
        flash("O arquivo XLSX está aberto no Excel. Feche-o e tente novamente.", "danger")
        return False
    return True

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def substituir_placeholder(doc, placeholder, texto):
    for p in doc.paragraphs:
        for run in p.runs:
            if placeholder in run.text:
                run.text = run.text.replace(placeholder, texto)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for run in p.runs:
                        if placeholder in run.text:
                            run.text = run.text.replace(placeholder, texto)


# -------------------- Gerar Layout Apdata --------------------
@geralayout_bp.route('/apdata', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if not file.filename.endswith('.xlsx'):
                flash("Envie um arquivo .xlsx válido", "danger")
                return redirect(url_for('geralayout'))
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            if not verificar_arquivo(path):
                return redirect(url_for('geralayout'))
            try:
                xls = pd.ExcelFile(path, engine='openpyxl')
            except Exception:
                flash("Erro ao abrir o arquivo Excel.", "danger")
                return redirect(url_for('geralayout'))
            abas = xls.sheet_names
            if not abas:
                flash("O arquivo não contém abas válidas", "warning")
                return redirect(url_for('geralayout'))
            session['uploaded_file'] = file.filename
            session['abas'] = abas
            return render_template('geralayout.html', abas=abas)
        elif any(key.startswith('transacao_') for key in request.form.keys()):
            uploaded_file = session.get('uploaded_file')
            if not uploaded_file:
                flash("Arquivo não encontrado. Faça upload novamente.", "danger")
                return redirect(url_for('geralayout'))
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], uploaded_file)
            if not verificar_arquivo(path):
                return redirect(url_for('geralayout'))
            try:
                xls = pd.ExcelFile(path, engine='openpyxl')
            except Exception:
                flash("Erro ao abrir o arquivo Excel.", "danger")
                return redirect(url_for('geralayout'))
            abas = session.get('abas', [])
            transacoes = {}
            for aba in abas:
                valor = request.form.get(f"transacao_{aba}", "").strip()
                if not valor:
                    flash(f"Informe a transação para a aba '{aba}'", "warning")
                    return redirect(url_for('geralayout'))
                transacoes[aba] = valor
            session['transacoes'] = transacoes
            return redirect(url_for('geralayout.gerar'))
    return render_template('geralayout.html')

@geralayout_bp.route('/gerar')
def gerar():
    filename = session.get('uploaded_file')
    transacoes = session.get('transacoes', {})
    abas = session.get('abas', [])
    if not filename or not transacoes:
        flash("Arquivo ou transações não encontradas. Faça o upload novamente.", "danger")
        return redirect(url_for('geralayout'))
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not verificar_arquivo(path):
        return redirect(url_for('geralayout'))
    try:
        xls = pd.ExcelFile(path, engine='openpyxl')
    except Exception:
        flash("Erro ao abrir o arquivo Excel.", "danger")
        return redirect(url_for('geralayout'))
    arquivos_gerados = []
    for aba in abas:
        df = pd.read_excel(xls, sheet_name=aba, header=None)
        if len(df) < 3:
            flash(f"Aba '{aba}' não possui linhas suficientes para gerar o layout.", "warning")
            continue
        valor_fixo = transacoes.get(aba, "")
        aba_sanitizada = re.sub(r'[\\/*?:"<>|]', "_", aba)
        txt_file = f"{aba_sanitizada}.txt"
        txt_path = os.path.join(current_app.config['GENERATED_FOLDER'], txt_file)
        with open(txt_path, 'w', encoding='cp1252', errors='replace') as f:
            codigos = df.iloc[1]
            for index in range(2, len(df)):
                linha = f"{valor_fixo};"
                for i in range(len(codigos)):
                    codigo = str(codigos[i]).strip().replace(" ", "")
                    valor = str(df.iloc[index, i]).strip() if not pd.isna(df.iloc[index, i]) else ""
                    linha += f"{codigo};({valor})"
                f.write(linha + "\n")
        arquivos_gerados.append(txt_path)
    if not arquivos_gerados:
        flash("Nenhum arquivo pôde ser gerado. Verifique o conteúdo das abas.", "danger")
        return redirect(url_for('geralayout'))
    session['arquivos_gerados'] = [os.path.basename(txt) for txt in arquivos_gerados]
    arquivos_preview = []
    for txt in arquivos_gerados:
        with open(txt, 'r', encoding='cp1252', errors='replace') as f:
            arquivos_preview.append({"filename": os.path.basename(txt), "conteudo": f.read()})
    return render_template('preview.html', arquivos=arquivos_preview)

@geralayout_bp.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(current_app.config['GENERATED_FOLDER'], filename, as_attachment=True)

@geralayout_bp.route('/download_all')
def download_all():
    arquivos_para_zip = session.get('arquivos_gerados', [])
    if not arquivos_para_zip:
        flash("Nenhum arquivo disponível para download.", "warning")
        return redirect(url_for('geralayout'))
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for filename in arquivos_para_zip:
            caminho = os.path.join(current_app.config['GENERATED_FOLDER'], filename)
            if os.path.exists(caminho):
                zf.write(caminho, filename)
    memory_file.seek(0)
    return send_file(memory_file, download_name='arquivos_txt.zip', as_attachment=True)

