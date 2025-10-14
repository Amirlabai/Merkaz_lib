import os
import shutil
import zipfile
from io import BytesIO
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, session, send_from_directory, send_file, abort, flash, request

import config
from utils import log_event

files_bp = Blueprint('files', __name__)

@files_bp.route('/')
@files_bp.route('/browse/', defaults={'subpath': ''})
@files_bp.route('/browse/<path:subpath>')
def downloads(subpath=''):
    if not session.get("logged_in"): return redirect(url_for("auth.login"))
    
    share_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.SHARE_FOLDER)

    safe_subpath = os.path.normpath(subpath).replace('\\', '/')
    if safe_subpath == '.':
        safe_subpath = ''
        
    if '/.' in safe_subpath:
        return abort(404)
        
    current_path = os.path.join(share_dir, safe_subpath)
    
    if not os.path.abspath(current_path).startswith(os.path.abspath(share_dir)):
        return abort(403)

    items = []
    if os.path.exists(current_path) and os.path.isdir(current_path):
        for item_name in os.listdir(current_path):
            if item_name.startswith('.'): continue
            item_path_os = os.path.join(current_path, item_name)
            item_path_url = os.path.join(safe_subpath, item_name).replace('\\', '/')
            items.append(
                {"name": item_name, "is_folder": os.path.isdir(item_path_os), "path": item_path_url})
    
    items.sort(key=lambda x: (not x['is_folder'], x['name'].lower()))
    
    back_path = os.path.dirname(safe_subpath).replace('\\', '/') if safe_subpath else None

    return render_template("downloads.html", 
                           items=items, 
                           current_path=safe_subpath, 
                           back_path=back_path,
                           suggestion_error=session.pop('suggestion_error', None),
                           suggestion_success=session.pop('suggestion_success', None),
                           cooldown_level=session.get("cooldown_index", 0) + 1,
                           is_admin=session.get('is_admin', False))


@files_bp.route("/delete/<path:item_path>", methods=["POST"])
def delete_item(item_path):
    if not session.get("is_admin"): abort(403)
    
    share_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.SHARE_FOLDER)
    trash_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.TRASH_FOLDER)

    source_path = os.path.join(share_dir, item_path)

    if not os.path.exists(source_path) or not source_path.startswith(share_dir):
        flash("File or folder not found.", "error")
        return redirect(request.referrer or url_for('files.downloads'))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(item_path)
    dest_name = f"{timestamp}_{base_name}"
    dest_path = os.path.join(trash_dir, dest_name)

    try:
        shutil.move(source_path, dest_path)
        flash(f"Successfully moved '{base_name}' to trash.", "success")
        log_event(config.DOWNLOAD_LOG_FILE, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session.get("email", "unknown"), "DELETE", item_path])
    except Exception as e:
        flash(f"Error deleting item: {e}", "error")

    parent_folder = os.path.dirname(item_path)
    if parent_folder:
        return redirect(url_for('files.downloads', subpath=parent_folder))
    return redirect(url_for('files.downloads'))

@files_bp.route("/download/file/<path:file_path>")
def download_file(file_path):
    if not session.get("logged_in"): return redirect(url_for("auth.login"))
    log_event(config.DOWNLOAD_LOG_FILE, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session.get("email", "unknown"), "FILE", file_path])
    share_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.SHARE_FOLDER)

    directory, filename = os.path.split(file_path)
    safe_dir = os.path.join(share_dir, directory)
    if not safe_dir.startswith(share_dir) or not os.path.isdir(safe_dir): return abort(403)
    return send_from_directory(safe_dir, filename, as_attachment=True)

@files_bp.route("/download/folder/<path:folder_path>")
def download_folder(folder_path):
    if not session.get("logged_in"): return redirect(url_for("auth.login"))
    log_event(config.DOWNLOAD_LOG_FILE, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session.get("email", "unknown"), "FOLDER", folder_path])
    share_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.SHARE_FOLDER)

    absolute_folder_path = os.path.join(share_dir, folder_path)
    if not os.path.isdir(absolute_folder_path) or not absolute_folder_path.startswith(share_dir): return abort(404)
    
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(absolute_folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zf.write(file_path, os.path.relpath(file_path, absolute_folder_path))
    memory_file.seek(0)
    return send_file(memory_file, download_name=f'{os.path.basename(folder_path)}.zip', as_attachment=True)

COOLDOWN_LEVELS = [60, 300, 600, 1800, 3600]
@files_bp.route("/suggest", methods=["POST"])
def suggest():
    if not session.get("logged_in"): return redirect(url_for("auth.login"))
    suggestion_text = request.form.get("suggestion")
    if not suggestion_text: return redirect(url_for("files.downloads"))
    
    now = datetime.now()
    last_suggestion_time_str = session.get("last_suggestion_time")
    cooldown_index = session.get("cooldown_index", 0)
    
    if last_suggestion_time_str:
        last_suggestion_time = datetime.fromisoformat(last_suggestion_time_str)
        if last_suggestion_time.date() < now.date() and cooldown_index > 0:
            cooldown_index = 0
            session["cooldown_index"] = 0
        elapsed_time = (now - last_suggestion_time).total_seconds()
        current_cooldown = COOLDOWN_LEVELS[cooldown_index]
        if elapsed_time < current_cooldown:
            remaining = max(1, round((current_cooldown - elapsed_time) / 60))
            session['suggestion_error'] = f"You must wait another {remaining} minute(s) before submitting again."
            return redirect(url_for('files.downloads'))
            
    log_event(config.SUGGESTION_LOG_FILE, [now.strftime("%Y-%m-%d %H:%M:%S"), session.get("email", "unknown"), suggestion_text])
    session["last_suggestion_time"] = now.isoformat()
    if cooldown_index < len(COOLDOWN_LEVELS) - 1:
        session["cooldown_index"] = cooldown_index + 1
    session['suggestion_success'] = "Thank you, your suggestion has been submitted!"
    return redirect(url_for("files.downloads"))
