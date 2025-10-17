# Merkaz\_lib

Merkaz\_lib is a secure, web-based file-sharing platform designed for students. It allows users to register, upload files for review, and share them with others in an organized library. The platform is managed by administrators who have full control over user approvals, file management, and content organization.

## Features

  * **User Authentication:** A secure registration and login system. New user accounts require administrator approval, ensuring a controlled user base.
  * **File Sharing Library:** An intuitive file browser for users to navigate, download, and share approved files and folders.
  * **Admin Dashboard:** A comprehensive dashboard for administrators to:
      * Manage users (approve, deny, or make other users admins).
      * Review and approve or decline user-uploaded files.
      * Create new folders directly within the file library.
      * Download activity logs for sessions, downloads, and user suggestions.
  * **Secure File Uploads:**
      * **Tiered Size Limits:** Different upload size limits for images, videos, and general files to manage server resources effectively.
      * **Virus Scanning:** All uploaded files are automatically scanned for malware using a command-line antivirus engine (like ClamAV). Infected files are immediately rejected and deleted.
  * **Download Safety:** A warning page is shown before any download, advising users of the potential risks of downloading user-submitted content.
  * **User Feedback:** A suggestion box for users to provide feedback and ideas.

## Installation and Setup

To get started with Merkaz\_lib, you'll need Python installed on your system. It is highly recommended to use a virtual environment to manage the project's dependencies.

### 1\. Virtual Environment Setup

From the project's root directory:

```bash
# Create a virtual environment
python -m venv .venv

# Activate the environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate
```

If you encounter an execution policy error on PowerShell, you can allow scripts for the current session by running:
`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`

### 2\. Install Dependencies

Once the virtual environment is activated, install the required packages from `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 3\. Configuration

Before running the application, you must set up your configuration:

1.  Find the `config_template.py` file and create a copy of it named `config.py`.
2.  Open `config.py` and fill in the required values:
      * `SUPER_SECRET_KEY` and `TOKEN_SECRET_KEY`: Set these to long, random strings for security.
      * `MAIL_...`: Enter your Gmail credentials for sending email notifications. It's recommended to use a Google App Password.

### 4\. Running the Application

With the setup complete, you can start the application by running the `main.py` file:

```bash
python main.py
```

The server will start, and you can access the application at `http://localhost:8000`.

## Security: Virus Scanning

The application enhances security by scanning uploaded files for viruses. This feature relies on an external, command-line antivirus tool.

#### How it Works

The function `scan_file_for_viruses` in `utils.py` is designed to work with a scanner like **ClamAV**. When a file is uploaded, the script will:

1.  Temporarily save the file to the server.
2.  Execute the scanner's command-line tool (e.g., `clamscan`) on the file.
3.  If a virus is detected, the file is immediately deleted, and the upload is rejected.

#### Setup on Windows

1.  **Install a Scanner:** Download and install a command-line scanner, such as **ClamAV for Windows**.
2.  **Add to PATH:** Add the directory containing the scanner's executable (e.g., `clamscan.exe`) to your Windows `PATH` environment variable. This allows the Python script to find and run the scanner.

**Note:** If no scanner is found in the system's `PATH`, the virus scan will be skipped, and a warning will be printed to the console.

## Exposing to the Internet with Ngrok

To share your local server with others over the internet, you can use ngrok.

1.  Follow the setup instructions on the [ngrok website](https://dashboard.ngrok.com/get-started/setup).
2.  Once installed and configured, run the following command to create a public URL that tunnels to your local server:
    ```bash
    ngrok http 8000
    ```