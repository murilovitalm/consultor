import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask import Blueprint

# Criando o blueprint de "manuais"

comandos_bp = Blueprint("comandos", __name__, template_folder="../templates")

# -------------------- Comandos / Competências --------------------
@comandos_bp.route('/comandos')
def comandos():
    return render_template('comandos.html')

@comandos_bp.route('/competencias', methods=['GET', 'POST'])
def competencias():
    if request.method == 'POST':
        avaliado = request.form.get('avaliado')
        avaliador = request.form.get('avaliador')
        forma = request.form.get('forma')
        comando_sql = (
            f"SELECT * FROM Contratados "
            f"WHERE Con_CdiContratado='{avaliado}' "
            f"AND Con_CdiAvaliador='{avaliador}' "
            f"AND CON_CdiForma='{forma}'"
        )
        session['comando_sql'] = comando_sql
        return redirect(url_for('comandos.preview_comando'))
    return render_template('competencias.html')

@comandos_bp.route('/preview_comando')
def preview_comando():
    comando_sql = session.get('comando_sql')
    if not comando_sql:
        flash("Nenhum comando gerado.", "warning")
        return redirect(url_for('competencias'))
    return render_template('preview_comando.html', comando=comando_sql)