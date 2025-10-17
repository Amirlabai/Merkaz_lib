import os
import csv
import subprocess
from io import BytesIO
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from openpyxl.workbook import Workbook
except ImportError:
    print("Warning: openpyxl not found. Excel export will not work. Run 'pip install openpyxl'.")
    class Workbook: pass

def log_event(filename, data):
    """Appends a new row to a specified CSV log file."""
    with open(filename, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(data)

def scan_file_for_viruses(file_path): # change to windows defender var "scanner_command"
    """
    Scans a file for viruses using a command-line scanner (e.g., ClamAV).
    This is a placeholder and requires a real scanner to be installed on the server.
    
    Args:
        file_path (str): The absolute path to the file to be scanned.

    Returns:
        tuple: (is_malicious, message)
               - is_malicious (bool): True if a virus is found, False otherwise.
               - message (str): The output from the scanner or a status message.
    """
    # --- Example Integration for ClamAV ---
    # To make this work, you must install ClamAV on your server.
    # On Debian/Ubuntu: sudo apt-get install clamav
    # On CentOS/RHEL: sudo yum install clamav
    
    # Check if the scanner command exists.
    # You might need to adjust 'clamscan' to the actual command or its full path.
    scanner_command = "clamscan"
    if not any(os.access(os.path.join(path, scanner_command), os.X_OK) for path in os.environ["PATH"].split(os.pathsep)):
        print(f"WARNING: '{scanner_command}' not found in PATH. Virus scanning is disabled.")
        # In a production environment, you might want to prevent uploads if the scanner is down.
        # For this example, we'll just assume the file is clean.
        return (False, "Clean (Scanner Not Found)")

    try:
        # The command for clamscan to scan a file:
        # --no-summary: Don't print a summary at the end.
        # -i: Only print infected files.
        # file_path: The path to the file.
        result = subprocess.run([scanner_command, "--no-summary", "-i", file_path], capture_output=True, text=True)
        
        # If clamscan finds a virus, it will print the file path and "FOUND".
        # Its return code will be 1 for infected files, 0 for clean.
        if result.returncode == 1:
            return (True, result.stdout.strip())
        elif result.returncode == 0:
            return (False, "Clean")
        else:
            # Handle other return codes or errors from the scanner
            return (False, f"Scan Error: {result.stderr.strip()}")

    except FileNotFoundError:
        # This will be caught if the subprocess.run fails because the command doesn't exist.
        return (False, "Clean (Scanner Not Found)")
    except Exception as e:
        return (False, f"An unexpected error occurred during scanning: {e}")


def csv_to_xlsx_in_memory(csv_filepath):
    """Converts a CSV file to an XLSX file in memory (BytesIO)."""
    if 'Workbook' not in globals():
        raise RuntimeError("openpyxl library is missing.")
    wb = Workbook()
    ws = wb.active
    ws.title = os.path.basename(csv_filepath).replace('.csv', '').title()
    try:
        with open(csv_filepath, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                ws.append(row)
    except FileNotFoundError:
        ws.append(["Error", "File Not Found"])
    memory_file = BytesIO()
    wb.save(memory_file)
    memory_file.seek(0)
    return memory_file

def create_file_with_header(filename, header):
    """Creates a file with a header if it doesn't exist."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    if not os.path.exists(filename):
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(header)
        print(f"Created file: {filename}")