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

app = Flask(__name__)

# Configuration - CHANGE THIS PASSWORD IN PRODUCTION
app.secret_key = 'your-secret-key-change-this-in-production'
ADMIN_PASSWORD = 'admin123'  # Change this to your desired password

# Server configuration
HOST = '0.0.0.0'
PORT = 8443
DEBUG = False
USE_HTTPS = False  # Set to True to enable HTTPS with self-signed certificates

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
    <title>Login - Automation Dashboard</title>
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
            <h2>Automation Dashboard</h2>
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
                <input type="text" class="form-control" id="username" name="username" value="admin" readonly>
            </div>
            <div class="mb-3">
                <label for="password" class="form-label">Password</label>
                <input type="password" class="form-control" id="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary btn-login w-100">Sign In</button>
        </form>
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
    <title>Dashboard - Automation Dashboard</title>
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
                <i class="bi bi-rocket-takeoff"></i> Automation Dashboard
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
                            <div class="mb-4">
                                <label for="inventory" class="form-label">Inventory</label>
                                <select class="form-select" id="inventory" name="inventory" required>
                                    <option value="">Select inventory...</option>
                                    {% for inv in inventories %}
                                        <option value="{{ inv }}">{{ inv }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="text-center">
                                <button type="submit" class="btn btn-success btn-execute">
                                    <i class="bi bi-play-fill"></i> Execute
                                </button>
                            </div>
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
    <title>Logs - Automation Dashboard</title>
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
                <i class="bi bi-rocket-takeoff"></i> Automation Dashboard
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
                        {% if log_files %}
                            <div class="list-group list-group-flush">
                                {% for log_file in log_files %}
                                    <a href="#" class="list-group-item list-group-item-action log-item" 
                                       onclick="loadLogContent('{{ log_file.name }}')">
                                        <div class="d-flex w-100 justify-content-between">
                                            <h6 class="mb-1">{{ log_file.name }}</h6>
                                            <small>{{ log_file.modified }}</small>
                                        </div>
                                        <small class="text-muted">{{ log_file.size }} bytes</small>
                                    </a>
                                {% endfor %}
                            </div>
                        {% else %}
                            <div class="text-center py-4 text-muted">
                                <i class="bi bi-inbox fs-1"></i>
                                <p class="mt-2">No log files found</p>
                            </div>
                        {% endif %}
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
def get_files_by_extension(directory, extension):
    """Get files with specific extension from directory"""
    if not os.path.exists(directory):
        return []
    pattern = os.path.join(directory, f'*.{extension}')
    return [os.path.basename(f) for f in glob.glob(pattern)]

def get_log_files():
    """Get log files with metadata"""
    if not os.path.exists(LOGS_DIR):
        return []
    
    log_files = []
    for filename in os.listdir(LOGS_DIR):
        filepath = os.path.join(LOGS_DIR, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            log_files.append({
                'name': filename,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    # Sort by modification time (newest first)
    log_files.sort(key=lambda x: x['modified'], reverse=True)
    return log_files

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
        
        if username == 'admin' and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get available files for each type
    playbook_files = get_files_by_extension(PLAYBOOKS_DIR, 'yml')
    powershell_files = get_files_by_extension(PLAYBOOKS_DIR, 'ps1')
    shell_files = get_files_by_extension(PLAYBOOKS_DIR, 'sh')
    inventories = get_files_by_extension(INVENTORY_DIR, 'ini')
    
    return render_template_string(DASHBOARD_TEMPLATE,
                                playbook_files=playbook_files,
                                powershell_files=powershell_files,
                                shell_files=shell_files,
                                inventories=inventories)

@app.route('/execute_task', methods=['POST'])
@login_required
def execute_task():
    task_type = request.form.get('task_type')
    target_file = request.form.get('target_file')
    inventory = request.form.get('inventory')
    
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
            'python3', script_wrapper,
            '--playbooks', playbook_path,
            '--inventory', inventory_path
        ]
        
        # Run in background (non-blocking)
        subprocess.Popen(command, 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        flash(f'Job started successfully: {task_type} - {target_file}')
        
    except Exception as e:
        flash(f'Error starting job: {str(e)}')
    
    return redirect(url_for('dashboard'))

@app.route('/logs')
@login_required
def logs():
    log_files = get_log_files()
    return render_template_string(LOGS_TEMPLATE, log_files=log_files)

@app.route('/api/log/<filename>')
@login_required
def api_log_content(filename):
    """API endpoint to get log file content"""
    filepath = os.path.join(LOGS_DIR, filename)
    
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
    print(f"Login with username: admin, password: {ADMIN_PASSWORD}")
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