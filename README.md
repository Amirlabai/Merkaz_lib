# Merkaz_lib
An open library for file-sharing among students.

## Installation
To get started with Merkaz_lib, you'll need to have Python installed on your system. You can then clone the repository and install the necessary dependencies.


## Virtual Environment Setup
It is highly recommended to use a virtual environment to manage the project's dependencies. Here's how to set one up:

### Establish venv
```bash
python -m venv .venv
```

### Activate venv
On Windows (PowerShell):
```bash
.venv\Scripts\Activate.ps1
```
If you encounter an error, you may need to change the execution policy for the current process:
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

### Deactivate venv
```bash
.venv\Scripts\deactivate.ps1
```

### Installing Dependencies
Once the virtual environment is activated, you can install the required packages using pip.
```bash
pip install -r requirements.txt
```
(Note: This command may fail due to the encoding issue mentioned earlier.)

### Generating `requirements.txt`
If you add or update dependencies, you can regenerate the `requirements.txt` file with the following command:
```bash
pip freeze > requirements.txt
```

## Ngrok Setup
To expose the local server to the internet, you can use ngrok.
visit the website https://dashboard.ngrok.com/get-started/setup/windows and follow the steps, options for MacOs and linux appear above

### Example
```bash
ngrok http 8000
```
This command will create a public URL that tunnels to your local server running on port 8000.
