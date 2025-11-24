#!/usr/bin/env python3
"""
Flask Web GUI for Python Automation Scripts
A simple, secure, lightweight web interface to trigger existing Python automation scripts
"""

import os
import subprocess
import glob
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
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
        return render_template('pages/config_error.html'), 503

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

# Templates moved to separate template files

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

def build_breadcrumbs(current_path):
    """Build breadcrumb entries for the logs explorer"""
    breadcrumbs = [{'name': 'Logs', 'path': None}]
    if current_path:
        parts = current_path.strip('/').split('/')
        accumulated = []
        for part in parts:
            accumulated.append(part)
            breadcrumbs.append({
                'name': part,
                'path': '/'.join(accumulated)
            })
    return breadcrumbs

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
    
    return render_template('pages/login.html')

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
    
    return render_template(
        'pages/dashboard.html',
        playbook_files=playbook_files,
        powershell_files=powershell_files,
        shell_files=shell_files,
        inventory_files=inventory_files
    )

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
    raw_path = request.args.get('path', '')
    current_path = raw_path.strip('/') if raw_path else ''
    directories, files = get_log_files(current_path)
    
    # Calculate parent path - handle forward slashes properly
    parent_path = None
    if current_path:
        # Split by forward slash and remove last part
        parts = current_path.split('/')
        if len(parts) > 1:
            parent_path = '/'.join(parts[:-1])
        elif len(parts) == 1 and parts[0]:
            parent_path = None  # At root level
            
    return render_template(
        'pages/logs.html',
        directories=directories,
        files=files,
        current_path=current_path,
        parent_path=parent_path,
        breadcrumbs=build_breadcrumbs(current_path)
    )

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