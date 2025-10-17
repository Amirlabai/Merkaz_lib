# --- File Paths ---
SHARE_FOLDER = "files_to_share"
TRASH_FOLDER = "trash"  # Directory for deleted files
UPLOAD_FOLDER = "uploads" # Temp folder for user uploads

# --- User Databases ---
AUTH_USER_DATABASE = "data/auth_users.csv"
NEW_USER_DATABASE = "data/new_users.csv"
DENIED_USER_DATABASE = "data/denied_users.csv"
PASSWORD_RESET_DATABASE = "data/password_reset.csv"


# --- Log Files ---
SESSION_LOG_FILE = "logs/session_log.csv"
DOWNLOAD_LOG_FILE = "logs/download_log.csv"
SUGGESTION_LOG_FILE = "logs/suggestion_log.csv"
UPLOAD_LOG_FILE = "logs/upload_log.csv"
DECLINED_UPLOAD_LOG_FILE = "logs/declined_log.csv"

# --- Security ---
SUPER_SECRET_KEY = "your_super_secret_key_here" # Change this to a random string
TOKEN_SECRET_KEY = "another_secret_key" # Change this to a different random string

# --- Upload Limits (in megabytes) ---
MAX_IMAGE_SIZE_MB = 5
MAX_VIDEO_SIZE_MB = 100
MAX_FILE_SIZE_MB = 20
MAX_ADMIN_UPLOAD_SIZE_MB = 500  # Set a high limit for admins

# --- Allowed File Extensions ---
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'wmv'}
ALLOWED_FILE_EXTENSIONS = {'txt', 'pdf', 'zip', 'rar', '7z', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

# --- Combined Set for General Validation ---
ALL_ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS.union(ALLOWED_VIDEO_EXTENSIONS).union(ALLOWED_FILE_EXTENSIONS)


# --- Mail Server ---
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USERNAME = 'your_email@gmail.com'
MAIL_PASSWORD = 'app password from google'
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_DEFAULT_SENDER = 'your_email@gmail.com'