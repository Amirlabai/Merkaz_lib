import os
import csv
import shutil
import magic
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort

import config
from utils import log_event

uploads_bp = Blueprint('uploads', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

def is_file_malicious(file_stream):
    """
    Checks the magic number of a file to determine if it's potentially malicious.
    """
    file_signature = file_stream.read(2048)  # Read the first 2048 bytes
    file_stream.seek(0)  # Reset stream position
    
    file_type = magic.from_buffer(file_signature, mime=True)

    # Add more sophisticated checks here if needed
    if "executable" in file_type:
        return True
    
    return False


@uploads_bp.route("/upload", defaults={'subpath': ''}, methods=["GET", "POST"])
@uploads_bp.route("/upload/<path:subpath>", methods=["GET", "POST"])
def upload_file(subpath):
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
        
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.UPLOAD_FOLDER)
        
    if request.method == "POST":
        uploaded_files = request.files.getlist("file")
        if not uploaded_files or (len(uploaded_files) == 1 and uploaded_files[0].filename == ''):
            flash('No files selected.', 'error')
            return redirect(request.url)
            
        upload_subpath = request.form.get('subpath', '')
        successful_uploads = []
        
        for file in uploaded_files:
            if file:
                if not allowed_file(file.filename):
                    flash(f"File type not allowed for {file.filename}", "error")
                    continue

                if is_file_malicious(file.stream):
                    flash(f"Malicious file detected: {file.filename}", "error")
                    continue
                # filename from the browser can include the relative path for folder uploads
                filename = file.filename
                
                # Security check to prevent path traversal attacks
                if '..' in filename.split('/') or '..' in filename.split('\\') or os.path.isabs(filename):
                    flash(f"Invalid path in filename: '{filename}' was skipped.", "error")
                    continue
                
                save_path = os.path.join(upload_dir, filename)

                # Final security check to ensure the path doesn't escape the upload directory
                if not os.path.abspath(save_path).startswith(os.path.abspath(upload_dir)):
                    flash(f"Invalid save path for file: '{filename}' was skipped.", "error")
                    continue

                try:
                    # Create parent directories if they don't exist
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    file.save(save_path)
                    
                    # The suggested path for the file after admin approval
                    final_path_suggestion = os.path.join(upload_subpath, filename).replace('\\', '/')
                    
                    log_event(config.UPLOAD_LOG_FILE, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session.get("email"), filename, final_path_suggestion])
                    successful_uploads.append(filename)
                except Exception as e:
                    flash(f"Could not upload '{filename}'. Error: {e}", "error")

        if successful_uploads:
            flash(f'Successfully uploaded {len(successful_uploads)} file(s). Files are pending review.', 'success')
        
        return redirect(url_for('files.downloads', subpath=upload_subpath))

    return render_template('upload.html', subpath=subpath)

@uploads_bp.route('/my_uploads')
def my_uploads():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.UPLOAD_FOLDER)
    user_email = session.get('email')
    user_uploads = []
    
    declined_items = set()
    try:
        with open(config.DECLINED_UPLOAD_LOG_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['email'] == user_email:
                    declined_items.add(row['filename'])
    except FileNotFoundError:
        pass

    try:
        with open(config.UPLOAD_LOG_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['email'] == user_email:
                    full_relative_path = row['filename']
                    top_level_item = full_relative_path.split('/')[0].split('\\')[0]

                    if top_level_item in declined_items:
                        row['status'] = 'Declined'
                    elif os.path.exists(os.path.join(upload_dir, full_relative_path)):
                        row['status'] = 'Pending Review'
                    else:
                        row['status'] = 'Approved & Moved'
                    user_uploads.append(row)
    except FileNotFoundError:
        pass

    user_uploads.reverse()
    return render_template('my_uploads.html', uploads=user_uploads)

@uploads_bp.route("/admin/uploads")
def admin_uploads():
    if not session.get("is_admin"):
        abort(403)
        
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes", ""), config.UPLOAD_FOLDER)
    grouped_uploads = {}
    
    # Check for newly selected paths from the browser session
    new_paths = session.get('new_paths', {})

    try:
        with open(config.UPLOAD_LOG_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            all_uploads_logged = list(reader)

        for row in reversed(all_uploads_logged):
            timestamp, email, relative_path, suggested_full_path = row[0], row[1], row[2], row[3]
            top_level_item = relative_path.split('/')[0].split('\\')[0]

            if top_level_item not in grouped_uploads:
                if os.path.exists(os.path.join(upload_dir, top_level_item)):
                    is_part_of_dir_upload = '/' in relative_path or '\\' in relative_path
                    # Get the original suggested path from the log
                    final_approval_path = os.path.dirname(suggested_full_path) if is_part_of_dir_upload else suggested_full_path
                    
                    # If a new path was chosen in the browser, override the original path
                    if top_level_item in new_paths:
                        final_approval_path = new_paths[top_level_item]
                    
                    grouped_uploads[top_level_item] = {
                        "timestamp": timestamp, 
                        "email": email, 
                        "filename": top_level_item,
                        "path": final_approval_path
                    }
    except (FileNotFoundError, StopIteration):
        pass

    # Clean up the session so paths don't stick around on the next page load
    if 'new_paths' in session:
        session.pop('new_paths', None)
        
    final_uploads_list = sorted(list(grouped_uploads.values()), key=lambda x: x['timestamp'])
    return render_template("admin_uploads.html", uploads=final_uploads_list)


@uploads_bp.route("/admin/move_upload/<path:filename>", methods=["POST"])
def move_upload(filename):
    if not session.get("is_admin"):
        abort(403)
        
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.UPLOAD_FOLDER)
    share_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.SHARE_FOLDER)
    
    target_path_str = request.form.get("target_path")
    if not target_path_str:
        flash("Target path cannot be empty.", "error")
        return redirect(url_for("uploads.admin_uploads"))

    source_item = os.path.join(upload_dir, filename)
    # Correctly handle if the target path is a directory or a full file path
    if os.path.isdir(source_item):
        destination_path = os.path.join(share_dir, target_path_str, filename)
    else:
        destination_path = os.path.join(share_dir, target_path_str)

    
    safe_destination_dir = os.path.abspath(os.path.dirname(destination_path))
    if not safe_destination_dir.startswith(os.path.abspath(share_dir)):
        flash("Invalid target path.", "error")
        return redirect(url_for("uploads.admin_uploads"))

    try:
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        shutil.move(source_item, destination_path)
        flash(f'Item "{filename}" has been successfully moved.', "success")
    except FileNotFoundError:
        flash(f'Error: Source item "{filename}" not found.', "error")
    except Exception as e:
        flash(f"An error occurred while moving the item: {e}", "error")

    return redirect(url_for("uploads.admin_uploads"))

@uploads_bp.route("/admin/decline_upload/<path:filename>", methods=["POST"])
def decline_upload(filename):
    if not session.get("is_admin"):
        abort(403)
        
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("routes",""), config.UPLOAD_FOLDER)
    item_to_delete = os.path.join(upload_dir, filename)
    user_email = request.form.get("email", "unknown")
    
    log_event(config.DECLINED_UPLOAD_LOG_FILE, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_email, filename])

    try:
        if os.path.exists(item_to_delete):
            if os.path.isdir(item_to_delete):
                shutil.rmtree(item_to_delete)
            else:
                os.remove(item_to_delete)
            flash(f'Item "{filename}" has been declined and removed.', "success")
        else:
            flash(f'Item "{filename}" was already removed.', "error")
    except Exception as e:
        flash(f"An error occurred while declining the item: {e}", "error")

    return redirect(url_for("uploads.admin_uploads"))

