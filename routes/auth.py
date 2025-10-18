import re
import csv
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash
from werkzeug.security import generate_password_hash
import config
from user import User
from utils import log_event
from mailer import send_new_user_notification, send_password_reset_email
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

auth_bp = Blueprint('auth', __name__)

def email_exists(email):
    """Checks if an email exists in auth, pending, or denied users."""
    return User.find_by_email(email) or User.find_pending_by_email(email) or User.find_denied_by_email(email)

@auth_bp.before_request
def before_request():
    """Reset the session timer with each request."""
    session.permanent = True

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    email_value = ""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        email_value = email

        user = User.find_by_email(email)
        login_success = False

        if user and user.check_password(password):
            if user.is_active:
                session["logged_in"] = True
                session["email"] = user.email
                session["is_admin"] = user.is_admin
                login_success = True
            else:
                error = "Your account is inactive. Please contact an administrator."

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if login_success:
            log_event(config.SESSION_LOG_FILE, [timestamp, email, "LOGIN_SUCCESS"])
            # --- MODIFICATION START ---
            # Check for a 'next' URL in the session to redirect back.
            next_url = session.pop('next', None)
            return redirect(next_url or url_for("files.downloads"))
            # --- MODIFICATION END ---
        else:
            log_event(config.SESSION_LOG_FILE, [timestamp, email, "LOGIN_FAIL"])
            if not error:
                if User.find_pending_by_email(email):
                    error = "Your account is pending administrator approval."
                elif User.find_denied_by_email(email):
                    error = "Your registration has been denied."
                else:
                    error = "Invalid credentials. Please try again or register."

    return render_template("login.html", error=error, email=email_value)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    email_value = ""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        email_value = email
        if email_exists(email):
            error = "This email is already registered, pending approval, or has been denied."
            return render_template("register.html", error=error, email=email_value)
        if len(password) < 8:
            error = "Password must be at least 8 characters long."
        elif not re.search("[a-z]", password):
            error = "Password must contain a lowercase letter."
        elif not re.search("[A-Z]", password):
            error = "Password must contain an uppercase letter."
        elif not re.search("[0-9]", password):
            error = "Password must contain a number."
        elif not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
            error = "Password must contain a special character."
        if error: return render_template("register.html", error=error, email=email_value)

        hashed_password = generate_password_hash(password)
        with open(config.NEW_USER_DATABASE, mode='a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([email, hashed_password, 'user'])
        
        send_new_user_notification(current_app._get_current_object(), email)
        session['login_message'] = "Registration successful! Your account is now pending administrator approval."
        return redirect(url_for("auth.login"))
    return render_template("register.html", error=error, email=email_value)

@auth_bp.route("/logout")
def logout():
    log_event(config.SESSION_LOG_FILE, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session.get("email", "unknown"), "LOGOUT"])
    session.clear()
    return redirect(url_for("auth.login"))

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        user = User.find_by_email(email)
        if user:
            s = URLSafeTimedSerializer(config.TOKEN_SECRET_KEY)
            token = s.dumps(email, salt='password-reset-salt')
            send_password_reset_email(current_app._get_current_object(), email, token)
            flash("A password reset link has been sent to your email.", "success")
        else:
            flash("Email address not found.", "error")
        return redirect(url_for("auth.forgot_password"))
    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    s = URLSafeTimedSerializer(config.TOKEN_SECRET_KEY)
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour expiration
    except (SignatureExpired, BadTimeSignature):
        flash("The password reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form["password"]
        # Add password validation logic here (same as registration)
        users = User.get_all()
        user_found = False
        for user in users:
            if user.email == email:
                user.password = generate_password_hash(password)
                user_found = True
                break
        
        if user_found:
            User.save_all(users)
            flash("Your password has been updated successfully.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("An error occurred. Please try again.", "error")

    return render_template("reset_password.html", token=token)