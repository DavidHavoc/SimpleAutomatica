#!/usr/bin/env python3
"""
Flask Web GUI for Python Automation Scripts
A simple, secure, lightweight web interface to trigger existing Python automation scripts
"""

import os
import subprocess
import glob
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
from functools import wraps

import json
import sys

app = Flask(__name__)

# Load configuration
CONFIG_FILE = 'config.json'
CONFIG_ERROR = False

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config.json: {e}")
        return None

config = load_config()

if config:
    # Configuration
    app.secret_key = config.get('secret_key', 'default-insecure-secret-key')
    USERS = config.get('users', {})

    # Server configuration
    HOST = config.get('host', '0.0.0.0')
    PORT = config.get('port', 8443)
    DEBUG = config.get('debug', False)
    USE_HTTPS = config.get('use_https', False)
else:
    CONFIG_ERROR = True
    # Default settings just to serve the error page
    HOST = '0.0.0.0'
    PORT = 8443
    DEBUG = False
    USE_HTTPS = False
    USERS = {}
    app.secret_key = 'error-mode'

@app.before_request
def check_config():
    if CONFIG_ERROR:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Configuration Error</title>
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f8d7da; color: #721c24; }
                .container { text-align: center; padding: 2rem; background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                h1 { margin-bottom: 1rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Configuration Error</h1>
                <p>The application could not load <code>config.json</code>.</p>
                <p>Please ensure the file exists and contains valid JSON.</p>
            </div>
        </body>
        </html>
        """, 503

# Activity Logger
def log_activity(username, action, details=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] User: {username} | Action: {action}"
    if details:
        log_entry += f" | Details: {details}"
    
    log_file = os.path.join(LOGS_DIR, 'activity.log')
    with open(log_file, 'a') as f:
        f.write(log_entry + "\n")

# Directory paths
PLAYBOOKS_DIR = './playbooks'
INVENTORY_DIR = './inventory'
LOGS_DIR = './logs'

# Script wrappers
SCRIPT_WRAPPERS = {
    'ansible': './run_ansible.py',
    'powershell': './run_powershell_with_ansible.py',
    'shell': './run_sh_with_ansible.py'
}

# HTML Templates
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - simple_Automatica</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            padding: 2rem;
            max-width: 400px;
            width: 100%;
        }
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-header h2 {
            color: #333;
            font-weight: 600;
        }
        .form-control:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
        .btn-login {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            padding: 0.75rem;
            font-weight: 600;
        }
        .btn-login:hover {
            background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h2>simple_Automatica</h2>
            <p class="text-muted">Please sign in to continue</p>
        </div>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="mb-3">
                <label for="username" class="form-label">Username</label>
                <input type="text" class="form-control" id="username" name="username" required>
            </div>
            <div class="mb-3">
                <label for="password" class="form-label">Password</label>
                <input type="password" class="form-control" id="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary btn-login w-100">Sign In</button>
        </form>
        <div class="text-center mt-3 text-muted">
            <small>&copy; 2026 David Zhorzholiani</small>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - simple_Automatica</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .navbar-brand {
            font-weight: 600;
        }
        .dashboard-container {
            padding: 2rem;
        }
        .card {
            border: none;
            box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
        }
        .btn-execute {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            border: none;
            padding: 0.5rem 2rem;
        }
        .btn-execute:hover {
            background: linear-gradient(135deg, #218838 0%, #1ea085 100%);
        }
        .nav-link {
            transition: color 0.2s;
        }
        .nav-link:hover {
            color: #667eea !important;
        }
        .nav-link.active {
            color: #667eea !important;
            font-weight: 600;
        }
        .form-select:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="bi bi-rocket-takeoff"></i> simple_Automatica
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link {% if request.endpoint == 'dashboard' %}active{% endif %}" href="{{ url_for('dashboard') }}">
                    <i class="bi bi-speedometer2"></i> Dashboard
                </a>
                <a class="nav-link {% if request.endpoint == 'logs' %}active{% endif %}" href="{{ url_for('logs') }}">
                    <i class="bi bi-file-text"></i> Logs
                </a>
                <a class="nav-link text-danger" href="{{ url_for('logout') }}">
                    <i class="bi bi-box-arrow-right"></i> Logout
                </a>
            </div>
        </div>
    </nav>

    <div class="container dashboard-container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        <i class="bi bi-check-circle"></i> {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="card">
                    <div class="card-header bg-white py-3">
                        <h5 class="card-title mb-0">
                            <i class="bi bi-play-circle text-primary"></i> Execute Automation Task
                        </h5>
                    </div>
                    <div class="card-body">
                        <form method="POST" action="{{ url_for('execute_task') }}">
                            <div class="mb-3">
                                <label for="task_type" class="form-label">Task Type</label>
                                <select class="form-select" id="task_type" name="task_type" required>
                                    <option value="">Select task type...</option>
                                    <option value="ansible">Run Ansible Playbook</option>
                                    <option value="powershell">Run PowerShell Script</option>
                                    <option value="shell">Run Shell Script</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="target_file" class="form-label">Target File</label>
                                <select class="form-select" id="target_file" name="target_file" required disabled>
                                    <option value="">Select task type first...</option>
                                </select>
                            </div>
                            <div class="mb-3">
                <label for="inventory" class="form-label">Inventory File</label>
                <select class="form-select" id="inventory" name="inventory" required>
                    <option value="" selected disabled>Select inventory...</option>
                    {% for inv in inventory_files %}
                        <option value="{{ inv }}">{{ inv }}</option>
                    {% endfor %}
                </select>
            </div>

            <div class="row mb-3">
                <div class="col-md-6">
                    <label for="forks" class="form-label">Parallelism (Forks)</label>
                    <select class="form-select" id="forks" name="forks">
                        <option value="1" selected>1 (recommended)</option>
                        {% for i in range(2, 11) %}
                            <option value="{{ i }}">{{ i }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-6 d-flex align-items-end">
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="checkbox" value="true" id="verbose" name="verbose">
                        <label class="form-check-label" for="verbose">
                            Verbose Output
                        </label>
                    </div>
                </div>
            </div>

            <button type="submit" class="btn btn-primary w-100">Start Job</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const playbookFiles = {{ playbook_files | tojson }};
        const powershellFiles = {{ powershell_files | tojson }};
        const shellFiles = {{ shell_files | tojson }};

        document.getElementById('task_type').addEventListener('change', function() {
            const targetFileSelect = document.getElementById('target_file');
            targetFileSelect.innerHTML = '<option value="">Select file...</option>';
            
            let files = [];
            switch(this.value) {
                case 'ansible':
                    files = playbookFiles;
                    break;
                case 'powershell':
                    files = powershellFiles;
                    break;
                case 'shell':
                    files = shellFiles;
                    break;
            }
            
            files.forEach(file => {
                const option = document.createElement('option');
                option.value = file;
                option.textContent = file;
                targetFileSelect.appendChild(option);
            });
            
            targetFileSelect.disabled = files.length === 0;
        });
    </script>
    <footer class="text-center py-4 text-muted">
        <small>&copy; 2026 David Zhorzholiani</small>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

LOGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Logs - simple_Automatica</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .navbar-brand {
            font-weight: 600;
        }
        .logs-container {
            padding: 2rem;
        }
        .log-item {
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .log-item:hover {
            background-color: #f8f9fa;
        }
        .log-content {
            background-color: #f8f9fa;
            border-radius: 0.375rem;
            padding: 1rem;
            font-family: 'Courier New', monospace;
            font-size: 0.875rem;
            white-space: pre-wrap;
            max-height: 500px;
            overflow-y: auto;
        }
        .nav-link {
            transition: color 0.2s;
        }
        .nav-link:hover {
            color: #667eea !important;
        }
        .nav-link.active {
            color: #667eea !important;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="bi bi-rocket-takeoff"></i> simple_Automatica
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link {% if request.endpoint == 'dashboard' %}active{% endif %}" href="{{ url_for('dashboard') }}">
                    <i class="bi bi-speedometer2"></i> Dashboard
                </a>
                <a class="nav-link {% if request.endpoint == 'logs' %}active{% endif %}" href="{{ url_for('logs') }}">
                    <i class="bi bi-file-text"></i> Logs
                </a>
                <a class="nav-link text-danger" href="{{ url_for('logout') }}">
                    <i class="bi bi-box-arrow-right"></i> Logout
                </a>
            </div>
        </div>
    </nav>

    <div class="container logs-container">
        <div class="row">
            <div class="col-lg-4">
                <div class="card">
                    <div class="card-header bg-white py-3">
                        <h5 class="card-title mb-0">
                            <i class="bi bi-journal-text text-primary"></i> Log Files
                        </h5>
                    </div>
                    <div class="card-body p-0">
                        <div class="list-group list-group-flush">
                            {% if parent_path is not none %}
                                <a href="{{ url_for('logs', path=parent_path) }}" class="list-group-item list-group-item-action bg-light">
                                    <i class="bi bi-arrow-90deg-up"></i> ..
                                </a>
                            {% endif %}
                            
                            {% for dir in directories %}
                                <a href="{{ url_for('logs', path=dir.path) }}" class="list-group-item list-group-item-action">
                                    <div class="d-flex w-100 justify-content-between align-items-center">
                                        <div>
                                            <i class="bi bi-folder-fill text-warning me-2"></i>
                                            {{ dir.name }}
                                        </div>
                                    </div>
                                </a>
                            {% endfor %}

                            {% for file in files %}
                                <a href="#" class="list-group-item list-group-item-action log-item" 
                                   onclick="loadLogContent('{{ file.path }}')">
                                    <div class="d-flex w-100 justify-content-between">
                                        <div>
                                            <i class="bi bi-file-text me-2"></i>
                                            {{ file.name }}
                                        </div>
                                        <small>{{ file.modified }}</small>
                                    </div>
                                    <small class="text-muted ms-4">{{ file.size }} bytes</small>
                                </a>
                            {% endfor %}
                            
                            {% if not directories and not files %}
                                <div class="text-center py-4 text-muted">
                                    <i class="bi bi-inbox fs-1"></i>
                                    <p class="mt-2">No logs found</p>
                                </div>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-lg-8">
                <div class="card">
                    <div class="card-header bg-white py-3">
                        <h5 class="card-title mb-0">
                            <i class="bi bi-file-earmark-text text-primary"></i> 
                            <span id="log-title">Select a log file to view</span>
                        </h5>
                    </div>
                    <div class="card-body">
                        <div id="log-content" class="log-content">
                            <div class="text-center text-muted">
                                <i class="bi bi-arrow-left"></i> Select a log file from the left to view its content
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function loadLogContent(filename) {
            fetch(`/api/log/${filename}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('log-title').textContent = filename;
                    document.getElementById('log-content').textContent = data.content || 'Log file is empty';
                })
                .catch(error => {
                    console.error('Error loading log content:', error);
                    document.getElementById('log-content').textContent = 'Error loading log content';
                });
        }
    </script>
    <footer class="text-center py-4 text-muted">
        <small>&copy; 2026 David Zhorzholiani</small>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper functions
# Helper functions
def is_safe_path(basedir, path, follow_symlinks=True):
    """Check if path is within basedir"""
    if follow_symlinks:
        matchpath = os.path.realpath(path)
    else:
        matchpath = os.path.abspath(path)
    basedir = os.path.realpath(basedir)
    return basedir == os.path.commonpath((basedir, matchpath))

def get_files_by_extension(directory, extension):
    """Get files with specific extension from directory"""
    if not os.path.exists(directory):
        return []
    pattern = os.path.join(directory, f'*.{extension}')
    return [os.path.basename(f) for f in glob.glob(pattern)]

def get_log_files(subdir=''):
    """Get log files and directories with metadata"""
    target_dir = os.path.join(LOGS_DIR, subdir)
    
    # Security check
    if not is_safe_path(os.path.abspath(LOGS_DIR), os.path.abspath(target_dir)):
        return [], []
        
    if not os.path.exists(target_dir):
        return [], []
    
    dirs = []
    files = []
    
    try:
        for filename in os.listdir(target_dir):
            filepath = os.path.join(target_dir, filename)
            # Use forward slashes for web paths
            relative_path = os.path.join(subdir, filename).replace('\\', '/')
            
            if os.path.isdir(filepath):
                dirs.append({
                    'name': filename,
                    'path': relative_path,
                    'type': 'dir'
                })
            elif os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    'name': filename,
                    'path': relative_path,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'file'
                })
    except OSError:
        pass
    
    dirs.sort(key=lambda x: x['name'])
    files.sort(key=lambda x: x['modified'], reverse=True)
    return dirs, files

# Routes
@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS and USERS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            log_activity(username, "LOGIN", "Successful login")
            return redirect(url_for('dashboard'))
        else:
            log_activity(username, "LOGIN_FAILED", "Invalid credentials")
            flash('Invalid username or password')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    if 'username' in session:
        log_activity(session['username'], "LOGOUT", "User logged out")
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get available files for each type
    playbook_files = get_files_by_extension(PLAYBOOKS_DIR, 'yml')
    powershell_files = get_files_by_extension(PLAYBOOKS_DIR, 'ps1')
    shell_files = get_files_by_extension(PLAYBOOKS_DIR, 'sh')
    inventory_files = get_files_by_extension(INVENTORY_DIR, 'ini')
    
    return render_template_string(DASHBOARD_TEMPLATE,
                                playbook_files=playbook_files,
                                powershell_files=powershell_files,
                                shell_files=shell_files,
                                inventory_files=inventory_files)

@app.route('/execute_task', methods=['POST'])
@login_required
def execute_task():
    task_type = request.form.get('task_type')
    target_file = request.form.get('target_file')
    inventory = request.form.get('inventory')
    verbose = request.form.get('verbose') == 'true'
    forks = request.form.get('forks', '1')
    
    if not all([task_type, target_file, inventory]):
        flash('Please fill in all fields')
        return redirect(url_for('dashboard'))
    
    # Validate script wrapper exists
    script_wrapper = SCRIPT_WRAPPERS.get(task_type)
    if not script_wrapper or not os.path.exists(script_wrapper):
        flash(f'Script wrapper not found: {script_wrapper}')
        return redirect(url_for('dashboard'))
    
    # Validate files exist
    playbook_path = os.path.join(PLAYBOOKS_DIR, target_file)
    inventory_path = os.path.join(INVENTORY_DIR, inventory)
    
    if not os.path.exists(playbook_path):
        flash(f'Target file not found: {playbook_path}')
        return redirect(url_for('dashboard'))
    
    if not os.path.exists(inventory_path):
        flash(f'Inventory file not found: {inventory_path}')
        return redirect(url_for('dashboard'))
    
    try:
        # Execute the command
        command = [
            sys.executable, script_wrapper,
            '--playbooks', playbook_path,
            '--inventory', inventory_path,
            '--forks', str(forks)
        ]
        
        if verbose:
            command.append('--verbose')
        
        # Run in background but capture output to a debug log
        debug_log = os.path.join(LOGS_DIR, 'debug_execution.log')
        with open(debug_log, 'a') as f:
            f.write(f"[{datetime.now()}] Starting command: {' '.join(command)}\n")
            
        # We use Popen but redirect to a file to debug
        with open(debug_log, 'a') as outfile:
            subprocess.Popen(command, 
                            stdout=outfile, 
                            stderr=outfile)
        
        log_activity(session['username'], "EXECUTE_TASK", f"Type: {task_type}, File: {target_file}, Inventory: {inventory}")
        flash(f'Job started successfully: {task_type} - {target_file}')
        
    except Exception as e:
        log_activity(session['username'], "EXECUTE_TASK_ERROR", f"Error: {str(e)}")
        flash(f'Error starting job: {str(e)}')
    
    return redirect(url_for('dashboard'))

@app.route('/logs')
@login_required
def logs():
    path = request.args.get('path', '')
    directories, files = get_log_files(path)
    
    # Calculate parent path
    parent_path = None
    if path:
        parent_path = os.path.dirname(path)
        if parent_path == '':
            parent_path = None
            
    return render_template_string(LOGS_TEMPLATE, 
                                directories=directories, 
                                files=files, 
                                current_path=path, 
                                parent_path=parent_path)

@app.route('/api/log/<path:filename>')
@login_required
def api_log_content(filename):
    """API endpoint to get log file content"""
    filepath = os.path.join(LOGS_DIR, filename)
    
    # Security check
    if not is_safe_path(os.path.abspath(LOGS_DIR), os.path.abspath(filepath)):
        return jsonify({'error': 'Access denied'}), 403
    
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Automation Dashboard...")
    print(f"Server will run on http{'s' if USE_HTTPS else ''}://{HOST}:{PORT}")
    print(f"Login with configured users")
    print(f"Playbooks directory: {PLAYBOOKS_DIR}")
    print(f"Inventory directory: {INVENTORY_DIR}")
    print(f"Logs directory: {LOGS_DIR}")
    
    # Create directories if they don't exist
    for directory in [PLAYBOOKS_DIR, INVENTORY_DIR, LOGS_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")
    
    # SSL context for HTTPS
    ssl_context = 'adhoc' if USE_HTTPS else None
    
    app.run(host=HOST, port=PORT, debug=DEBUG, ssl_context=ssl_context)