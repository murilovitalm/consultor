import os
from flask import render_template, request
from flask import Blueprint

# Criando o blueprint de "videos"

videos_bp = Blueprint("videos", __name__, template_folder="../templates")

VIDEO_FOLDER = os.path.join('static', 'videos')
os.makedirs(VIDEO_FOLDER, exist_ok=True)

# -------------------- Vídeo Aula --------------------
@videos_bp.route('/video-aula', methods=['GET', 'POST'])
def video_aula():
    termo = ""
    videos = [f for f in os.listdir(VIDEO_FOLDER) if os.path.isfile(os.path.join(VIDEO_FOLDER, f))]
    if request.method == 'POST':
        termo = request.form.get('termo', '').lower()
        if termo:
            videos = [v for v in videos if termo in v.lower()]
    return render_template('videos.html', videos=videos, termo=termo)