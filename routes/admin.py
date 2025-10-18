import os
from datetime import datetime
from flask import Blueprint, render_template, session, abort, redirect, url_for, flash, send_file, current_app, request

import config
from user import User
from utils import csv_to_xlsx_in_memory
from mailer import send_approval_email, send_denial_email

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
def require_admin():
    # 1. First, check if the user is logged in at all.
    if not session.get("logged_in"):
        flash("You must be logged in to access this page.", "error")
        # --- MODIFICATION START ---
        # Store the URL the user was trying to access.
        session['next'] = request.url
        # --- MODIFICATION END ---
        return redirect(url_for('auth.login'))
    
    # 2. If they are logged in, then check if they are an admin.
    if not session.get("is_admin"):
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for('files.downloads'))

@admin_bp.route("/metrics")
def admin_metrics():
    # The check is now handled by before_request
    log_files = [
        {"type": "session", "name": "Session Log (Login/Logout)", "description": "Track user login and failure events.", "format": "Excel"},
        {"type": "download", "name": "Download Log (File/Folder/Delete)", "description": "Track all file, folder, and delete events.", "format": "Excel"},
        {"type": "suggestion", "name": "Suggestion Log (User Feedback)", "description": "Records all user suggestions.", "format": "Excel"},
        {"type": "upload", "name": "Upload Log (User Submissions)", "description": "A record of all files uploaded by users.", "format": "CSV"}
    ]
    return render_template("admin_metrics.html", log_files=log_files)

@admin_bp.route("/users")
def admin_users():
    all_users = User.get_all()
    return render_template("admin_users.html", users=all_users, current_user_email=session.get('email'))

@admin_bp.route("/pending")
def admin_pending():
    pending_users = User.get_pending()
    return render_template("admin_pending.html", users=pending_users)

@admin_bp.route("/denied")
def admin_denied():
    denied_users = User.get_denied()
    return render_template("admin_denied.html", users=denied_users)

@admin_bp.route("/approve/<string:email>", methods=["POST"])
def approve_user(email):
    pending_users = User.get_pending()
    user_to_approve = next((user for user in pending_users if user.email == email), None)

    if user_to_approve:
        auth_users = User.get_all()
        user_to_approve.status = 'active'
        auth_users.append(user_to_approve)
        User.save_all(auth_users)

        remaining_pending = [user for user in pending_users if user.email != email]
        User.save_pending(remaining_pending)
        send_approval_email(current_app._get_current_object(), email)
        flash(f"User {email} has been approved.", "success")
    else:
        flash(f"Could not find pending user {email}.", "error")
    return redirect(url_for('admin.admin_pending'))

@admin_bp.route("/deny/<string:email>", methods=["POST"])
def deny_user(email):
    pending_users = User.get_pending()
    user_to_deny = next((user for user in pending_users if user.email == email), None)

    if user_to_deny:
        denied_users = User.get_denied()
        denied_users.append(user_to_deny)
        User.save_denied(denied_users)

        remaining_pending = [user for user in pending_users if user.email != email]
        User.save_pending(remaining_pending)
        send_denial_email(current_app._get_current_object(), email)
        flash(f"Registration for {email} has been denied.", "success")
    else:
        flash(f"Could not find pending user {email}.", "error")
    return redirect(url_for('admin.admin_pending'))

@admin_bp.route("/re_pend/<string:email>", methods=["POST"])
def re_pend_user(email):
    denied_users = User.get_denied()
    user_to_re_pend = next((user for user in denied_users if user.email == email), None)

    if user_to_re_pend:
        pending_users = User.get_pending()
        pending_users.append(user_to_re_pend)
        User.save_pending(pending_users)

        remaining_denied = [user for user in denied_users if user.email != email]
        User.save_denied(remaining_denied)
        flash(f"User {email} has been moved back to pending.", "success")
    else:
        flash(f"Could not find denied user {email}.", "error")
    return redirect(url_for('admin.admin_denied'))

@admin_bp.route("/toggle_role/<string:email>", methods=["POST"])
def toggle_role(email):
    if email == session.get('email'):
        flash("For security, you cannot change your own admin status.", "error")
        return redirect(url_for('admin.admin_users'))
    users = User.get_all()
    user_found = False
    for user in users:
        if user.email == email:
            user.role = 'user' if user.is_admin else 'admin'
            user_found = True
            break
    if user_found:
        User.save_all(users)
        flash(f"Successfully updated role for {email}.", "success")
    else:
        flash(f"Could not find user {email}.", "error")
    return redirect(url_for('admin.admin_users'))

@admin_bp.route("/toggle_status/<string:email>", methods=["POST"])
def toggle_status(email):
    if email == session.get('email'):
        flash("You cannot change your own status.", "error")
        return redirect(url_for('admin.admin_users'))
    users = User.get_all()
    user_found = False
    for user in users:
        if user.email == email:
            user.status = 'inactive' if user.is_active else 'active'
            user_found = True
            break
    if user_found:
        User.save_all(users)
        flash(f"Successfully updated status for {email}.", "success")
    else:
        flash(f"Could not find user {email}.", "error")
    return redirect(url_for('admin.admin_users'))

@admin_bp.route("/metrics/download/<log_type>")
def download_metrics(log_type):
    log_map = {
        "session": {"path": config.SESSION_LOG_FILE, "prefix": "Session_Log", "format": "xlsx"},
        "download": {"path": config.DOWNLOAD_LOG_FILE, "prefix": "Download_Log", "format": "xlsx"},
        "suggestion": {"path": config.SUGGESTION_LOG_FILE, "prefix": "Suggestion_Log", "format": "xlsx"},
        "upload": {"path": config.UPLOAD_LOG_FILE, "prefix": "Upload_Log", "format": "csv"}
    }

    if log_type not in log_map:
        abort(404)

    log_info = log_map[log_type]
    csv_filepath = log_info["path"]
    file_prefix = log_info["prefix"]
    file_format = log_info["format"]

    if not os.path.exists(csv_filepath):
        flash(f"Log file for '{log_type}' not found.", "error")
        return redirect(url_for('admin.admin_metrics'))

    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if file_format == "xlsx":
            xlsx_data = csv_to_xlsx_in_memory(csv_filepath)
            download_name = f"{file_prefix}_{timestamp}.xlsx"
            return send_file(xlsx_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                             download_name=download_name, as_attachment=True)
        elif file_format == "csv":
            download_name = f"{file_prefix}_{timestamp}.csv"
            return send_file(
                csv_filepath,
                mimetype='text/csv',
                download_name=download_name,
                as_attachment=True
            )
        else:
            return abort(400)
    except Exception as e:
        current_app.logger.error(f"Error during log download for '{log_type}': {e}")
        abort(500)