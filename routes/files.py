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
        folders = []
        files = []
        for item_name in os.listdir(current_path):
            if item_name.startswith('.'): continue
            
            item_path_os = os.path.join(current_path, item_name)
            item_path_url = os.path.join(safe_subpath, item_name).replace('\\', '/')
            
            item_data = {"name": item_name, "path": item_path_url}
            
            if os.path.isdir(item_path_os):
                item_data["is_folder"] = True
                folders.append(item_data)
            else:
                item_data["is_folder"] = False
                files.append(item_data)
        
        folders.sort(key=lambda x: x['name'].lower())
        files.sort(key=lambda x: x['name'].lower())
        
        items = folders + files
    
    back_path = os.path.dirname(safe_subpath).replace('\\', '/') if safe_subpath else None

    return render_template("downloads.html", 
                           items=items, 
                           current_path=safe_subpath, 
                           back_path=back_path,
                           suggestion_error=session.pop('suggestion_error', None),
                           suggestion_success=session.pop('suggestion_success', None),
                           cooldown_level=session.get("cooldown_index", 0) + 1,
                           is_admin=session.get('is_admin', False))


@files_bp.route("/create_folder", methods=["POST"])
def create_folder():
    if not session.get("is_admin"):
        abort(403)

    parent_path = request.form.get("parent_path", "")
    folder_name = request.form.get("folder_name", "").strip()

    if not folder_name:
        flash("Folder name cannot be empty.", "error")
        return redirect(url_for('files.downloads', subpath=parent_path))

    if '/' in folder_name or '\\' in folder_name or '..' in folder_name:
        flash("Invalid characters in folder name.", "error")
        return redirect(url_for('files.downloads', subpath=parent_path))

    share_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.SHARE_FOLDER)
    new_folder_path = os.path.join(share_dir, parent_path, folder_name)

    if not os.path.abspath(new_folder_path).startswith(os.path.abspath(share_dir)):
        flash("Invalid path.", "error")
        return redirect(url_for('files.downloads', subpath=parent_path))

    if os.path.exists(new_folder_path):
        flash(f"A folder or file named '{folder_name}' already exists.", "error")
    else:
        try:
            os.makedirs(new_folder_path)
            flash(f"Folder '{folder_name}' created successfully.", "success")
            log_event(config.DOWNLOAD_LOG_FILE, [datetime.now().strftime("%Y-%m-%d %H:%M%S"), session.get("email", "unknown"), "CREATE_FOLDER", os.path.join(parent_path, folder_name)])
        except Exception as e:
            flash(f"Error creating folder: {e}", "error")

    return redirect(url_for('files.downloads', subpath=parent_path))


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
        log_event(config.DOWNLOAD_LOG_FILE, [datetime.now().strftime("%Y-%m-%d %H:%M%S"), session.get("email", "unknown"), "DELETE", item_path])
    except Exception as e:
        flash(f"Error deleting item: {e}", "error")

    parent_folder = os.path.dirname(item_path)
    if parent_folder:
        return redirect(url_for('files.downloads', subpath=parent_folder))
    return redirect(url_for('files.downloads'))

# --- NEW: Download Warning Route ---
@files_bp.route("/download/warning/<path:item_path>")
def download_warning(item_path):
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))

    share_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.SHARE_FOLDER)
    full_path = os.path.join(share_dir, item_path)

    if not os.path.exists(full_path):
        abort(404)

    item_name = os.path.basename(item_path)
    confirm_url = ""

    if os.path.isdir(full_path):
        confirm_url = url_for('files.download_folder_confirmed', folder_path=item_path)
    else:
        confirm_url = url_for('files.download_file_confirmed', file_path=item_path)

    return render_template("download_warning.html", item_name=item_name, confirm_url=confirm_url)

# --- MODIFIED: Renamed to add '_confirmed' ---
@files_bp.route("/download/file/confirmed/<path:file_path>")
def download_file_confirmed(file_path):
    if not session.get("logged_in"): return redirect(url_for("auth.login"))
    log_event(config.DOWNLOAD_LOG_FILE, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session.get("email", "unknown"), "FILE", file_path])
    share_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.SHARE_FOLDER)

    directory, filename = os.path.split(file_path)
    safe_dir = os.path.join(share_dir, directory)
    if not safe_dir.startswith(share_dir) or not os.path.isdir(safe_dir): return abort(403)
    return send_from_directory(safe_dir, filename, as_attachment=True)

# --- MODIFIED: Renamed to add '_confirmed' ---
@files_bp.route("/download/folder/confirmed/<path:folder_path>")
def download_folder_confirmed(folder_path):
    if not session.get("logged_in"): return redirect(url_for("auth.login"))
    log_event(config.DOWNLOAD_LOG_FILE, [datetime.now().strftime("%Y-%m-%d %H:%M%S"), session.get("email", "unknown"), "FOLDER", folder_path])
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

# ... (rest of the file remains the same) ...
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
            
    log_event(config.SUGGESTION_LOG_FILE, [now.strftime("%Y-%m-%d %H:%M%S"), session.get("email", "unknown"), suggestion_text])
    session["last_suggestion_time"] = now.isoformat()
    if cooldown_index < len(COOLDOWN_LEVELS) - 1:
        session["cooldown_index"] = cooldown_index + 1
    session['suggestion_success'] = "Thank you, your suggestion has been submitted!"
    return redirect(url_for("files.downloads"))

@files_bp.route('/browse_for_path/', defaults={'subpath': ''}, methods=['GET', 'POST'])
@files_bp.route('/browse_for_path/<path:subpath>', methods=['GET'])
def browse_for_path(subpath=''):
    if not session.get("is_admin"):
        abort(403)

    # Handle POST request first (form submission to select a folder)
    if request.method == 'POST':
        filename = session.get('filename_for_path_change')
        if not filename:
            flash("Session expired or invalid request.", "error")
            return redirect(url_for('uploads.admin_uploads'))

        selected_path = request.form.get('selected_path', '')
        
        if 'new_paths' not in session:
            session['new_paths'] = {}
        session['new_paths'][filename] = selected_path
        session.modified = True
        
        session.pop('filename_for_path_change', None)
        return redirect(url_for('uploads.admin_uploads'))

    # --- Handle GET request (browsing folders) ---

    # If filename is in args, it's the initial entry from the "Edit" button. Store it in the session.
    if 'filename' in request.args:
        session['filename_for_path_change'] = request.args.get('filename')
    
    # Now, ensure the filename context exists in the session for navigation.
    filename = session.get('filename_for_path_change')
    if not filename:
        # If no filename in session, the user accessed the browser without clicking "Edit" first.
        return redirect(url_for('uploads.admin_uploads'))
    
    # Proceed with displaying the folder browser
    share_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes", ""), config.SHARE_FOLDER)
    
    safe_subpath = os.path.normpath(subpath).replace('\\', '/')
    if safe_subpath == '.': safe_subpath = ''
    if '/.' in safe_subpath: return abort(404)
        
    current_path = os.path.join(share_dir, safe_subpath)
    if not os.path.abspath(current_path).startswith(os.path.abspath(share_dir)): return abort(403)

    folders = []
    if os.path.exists(current_path) and os.path.isdir(current_path):
        for item_name in os.listdir(current_path):
            item_path_os = os.path.join(current_path, item_name)
            if os.path.isdir(item_path_os) and not item_name.startswith('.'):
                item_path_url = os.path.join(safe_subpath, item_name).replace('\\', '/')
                folders.append({"name": item_name, "path": item_path_url})
    
    folders.sort(key=lambda x: x['name'].lower())
    back_path = os.path.dirname(safe_subpath).replace('\\', '/') if safe_subpath else None

    return render_template("browse_for_path.html",
                           folders=folders,
                           current_path=safe_subpath,
                           back_path=back_path,
                           filename=filename)