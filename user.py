import csv
import config
from werkzeug.security import check_password_hash

# --- User Class ---
class User:
    def __init__(self, email, password, role='user', status='active'):
        self.email = email
        self.password = password  # This will now be a hashed password
        self.role = role
        self.status = status
        self.online_status = False # Add online status

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_active(self):
        return self.status == 'active'

    def check_password(self, password_to_check):
        """Checks the provided password against the stored hash."""
        return check_password_hash(self.password, password_to_check)

    # --- Methods for Authenticated Users (auth_users.csv) ---
    @staticmethod
    def find_by_email(email):
        """Finds a user by email in the authentication database."""
        return next((user for user in User.get_all() if user.email == email), None)

    @staticmethod
    def get_all():
        """Reads all users from the authentication database."""
        return User._read_users_from_file(config.AUTH_USER_DATABASE)

    @staticmethod
    def save_all(users):
        """Rewrites the entire auth user database."""
        User._save_users_to_file(config.AUTH_USER_DATABASE, users)

    @staticmethod
    def get_admin_emails():
        """Returns a list of all admin email addresses."""
        return [user.email for user in User.get_all() if user.is_admin]

    # --- Methods for Pending Users (new_users.csv) ---
    @staticmethod
    def find_pending_by_email(email):
        """Finds a user by email in the pending database."""
        return next((user for user in User.get_pending() if user.email == email), None)

    @staticmethod
    def get_pending():
        """Reads all users from the pending registration database."""
        return User._read_users_from_file(config.NEW_USER_DATABASE)

    @staticmethod
    def save_pending(users):
        """Rewrites the entire pending user database."""
        User._save_users_to_file(config.NEW_USER_DATABASE, users)

    # --- Methods for Denied Users (denied_users.csv) ---
    @staticmethod
    def find_denied_by_email(email):
        """Finds a user by email in the denied database."""
        return next((user for user in User.get_denied() if user.email == email), None)

    @staticmethod
    def get_denied():
        """Reads all users from the denied registration database."""
        return User._read_users_from_file(config.DENIED_USER_DATABASE)

    @staticmethod
    def save_denied(users):
        """Rewrites the entire denied user database."""
        User._save_users_to_file(config.DENIED_USER_DATABASE, users)

    # --- Private Helper Methods ---
    @staticmethod
    def _read_users_from_file(filepath):
        """Helper to read users from a given CSV file."""
        users = []
        try:
            with open(filepath, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None) # Skip header
                for row in reader:
                    if row and len(row) >= 3:
                        status = row[3] if len(row) > 3 else 'active'
                        users.append(User(email=row[0], password=row[1], role=row[2], status=status))
        except FileNotFoundError:
            return []
        return users

    @staticmethod
    def _save_users_to_file(filepath, users):
        """Helper to write a list of users to a given CSV file."""
        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["email", "password", "role", "status"]) # Write header
            for user in users:
                writer.writerow([user.email, user.password, user.role, user.status])