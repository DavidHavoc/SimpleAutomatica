# simple_Automatica - Flask Automation Dashboard

A sleek, secure web interface to trigger Python automation scripts with a modern dark theme featuring red accents.

## Features

- **Authentication**: Secure login system with configurable users
- **Dashboard**: Execute Ansible playbooks, PowerShell scripts, and shell scripts
- **Dynamic File Selection**: Automatically scans directories for available files
- **Log Viewer**: Browse and view log files with breadcrumb navigation
- **Modern UI**: Dark theme with red/burgundy/coral color scheme
- **Responsive Design**: Mobile-friendly interface using Bootstrap 5
- **HTTPS Support**: Optional self-signed certificate support
- **Activity Logging**: Tracks user actions and script executions
- **Interactive Help**: Hover tooltips for contextual information
- **Configurable**: JSON-based configuration for easy customization

## Design

The application features a modern dark theme with a sophisticated color palette:
- **Black Background**: `#0a0a0a` for the main interface
- **Burgundy**: `#872341` for gradients and accents
- **Red**: `#BE3144` for primary actions and highlights
- **Coral**: `#E17564` for hover states and interactive elements

## Requirements

- Python 3.6+
- Flask
- Existing automation scripts in the specified directories

## Installation

### 1. Install Flask
```bash
pip install flask
```

### 2. Set up Directory Structure
Ensure you have the following directory structure:

```
.
├── app.py                    # Main Flask application
├── config.json              # Configuration file (required)
├── templates/               # HTML templates
│   └── pages/
│       ├── login.html
│       ├── dashboard.html
│       ├── logs.html
│       └── config_error.html
├── playbooks/               # Directory containing .yml, .sh, .ps1 files
│   ├── example.yml
│   ├── script.sh
│   └── script.ps1
├── inventory/               # Directory containing .ini files
│   ├── hosts.ini
│   └── production.ini
├── logs/                    # Directory for log files (auto-created)
├── run_ansible.py          # Ansible wrapper script
├── run_powershell_with_ansible.py  # PowerShell wrapper script
└── run_sh_with_ansible.py  # Shell script wrapper
```

### 3. Configure the Application
Create a `config.json` file in the same directory as `app.py`:

```json
{
    "secret_key": "your-secret-key-change-this-in-production",
    "users": {
        "admin": "admin123",
        "user1": "password123"
    },
    "host": "0.0.0.0",
    "port": 8443,
    "debug": false,
    "use_https": false
}
```

**Important**: Change the `secret_key` and user passwords before deploying to production!

### 4. Enable HTTPS (Optional)
To enable HTTPS with self-signed certificates:

```json
{
    "use_https": true
}
```

**Note**: When using HTTPS for the first time, you'll see a browser warning about the self-signed certificate. This is normal - click "Advanced" and "Proceed" to continue.

## Running the Application

### Basic HTTP Server

```bash
python3 app.py
```

### HTTPS Server (with self-signed certificates)
1. Set `"use_https": true` in `config.json`
2. Run the application:
```bash
python3 app.py
```

The server will start on `http://0.0.0.0:8443` (or `https://` if HTTPS is enabled)

## Usage

### 1. Login
- Navigate to `http://your-server:8443` (or `https://your-server:8443` if HTTPS is enabled)
- Login with credentials configured in `config.json`
- Default: Username: `admin`, Password: `admin123` (change this!)

### 2. Dashboard - Execute Tasks
1. **Select Task Type** from the dropdown:
   - "Run Ansible Playbook" (uses `run_ansible.py`)
   - "Run PowerShell Script" (uses `run_powershell_with_ansible.py`)
   - "Run Shell Script" (uses `run_sh_with_ansible.py`)

2. **Select Target File** - automatically filtered based on task type:
   - `.yml` files for Ansible
   - `.ps1` files for PowerShell
   - `.sh` files for Shell scripts

3. **Select Inventory** - shows `.ini` files from the inventory directory

4. **Configure Options**:
   - **Parallelism (Forks)**: Set the number of parallel executions (1-10)
   - **Verbose Output**: Toggle verbose logging

5. Click **Start Job** to execute the command

**Tip**: Hover over the `?` icon in the hero card for helpful information about the dashboard.

### 3. Log Viewer
- Navigate to the **Logs** page from the navigation bar
- Use **breadcrumb navigation** to browse through log directories
- Click **".. (Go Up)"** to navigate to parent directories
- Click on any log file to view its content in the right panel
- **File dates** are displayed in red for easy visibility
- Log files are sorted by newest first

## Command Execution Logic

When you click "Start Job", the application runs:

```bash
python3 {selected_script_wrapper} --playbooks ./playbooks/{selected_file} --inventory ./inventory/{selected_inventory} --forks {forks} [--verbose]
```

The command is executed in the background using `subprocess.Popen()` so the web interface remains responsive.

## File Management

### Adding New Scripts
Simply place your files in the appropriate directories:

- **Ansible Playbooks**: `./playbooks/*.yml`
- **PowerShell Scripts**: `./playbooks/*.ps1`
- **Shell Scripts**: `./playbooks/*.sh`
- **Inventory Files**: `./inventory/*.ini`

The web interface will automatically detect and display them in the dropdowns.

### Log Files
Log files should be written to the `./logs/` directory by your automation scripts. The log viewer will automatically detect and display any files and subdirectories.

## Security Considerations

1. **Change default credentials** before deploying to production
2. **Use a strong secret_key** in `config.json`
3. **Enable HTTPS** in production environments
4. **Firewall**: Ensure only authorized IPs can access port 8443
5. **File permissions**: Set appropriate permissions on your script files
6. **Network security**: Consider using a reverse proxy (nginx/Apache) for additional security
7. **Path traversal protection**: The application includes built-in path validation to prevent directory traversal attacks

## Troubleshooting

### Common Issues

1. **"Configuration Error" page**
   - Ensure `config.json` exists in the same directory as `app.py`
   - Verify the JSON syntax is valid
   - Check file permissions

2. **"Script wrapper not found" error**
   - Ensure the wrapper scripts exist in the same directory as `app.py`
   - Check file permissions (should be executable)

3. **"Target file not found" error**
   - Verify your files are in the correct directories
   - Check file extensions match the expected types

4. **HTTPS Certificate Issues**
   - Self-signed certificates will show browser warnings - this is normal
   - For production, consider using proper SSL certificates (Let's Encrypt)

5. **Port Already in Use**
   - Change the `port` in `config.json`
   - Or stop the service using that port: `sudo netstat -tulpn | grep :8443`

6. **Logs page not loading**
   - Ensure the `./logs/` directory exists
   - Check directory permissions
   - Verify the `templates/pages/logs.html` file exists

### Debug Mode
For development, enable debug mode in `config.json`:

```json
{
    "debug": true
}
```

This will provide detailed error messages and auto-reload on code changes.

## Template Structure

The application uses Jinja2 templates organized in the `templates/pages/` directory:

- **`login.html`**: Authentication page with dark theme
- **`dashboard.html`**: Main interface with task execution form and hover tooltips
- **`logs.html`**: Log browser with breadcrumb navigation
- **`config_error.html`**: Error page displayed when `config.json` is missing or invalid

All templates share a consistent dark theme with red accents for a cohesive user experience.

## Running as a Service

For production deployment, run the application as a systemd service:

1. Create a service file: `/etc/systemd/system/simple-automatica.service`

```ini
[Unit]
Description=simple_Automatica Dashboard
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/SimpleAutomatica
ExecStart=/usr/bin/python3 /path/to/SimpleAutomatica/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Enable and start the service:
```bash
sudo systemctl enable simple-automatica
sudo systemctl start simple-automatica
sudo systemctl status simple-automatica
```

3. View logs:
```bash
sudo journalctl -u simple-automatica -f
```

## Activity Logging

All user actions are logged to `./logs/activity.log`:
- Login attempts (successful and failed)
- Task executions
- Errors and exceptions

Script execution output is logged to `./logs/debug_execution.log` for troubleshooting.

## Support

If you encounter issues:

1. Check the console output when running `python3 app.py`
2. Verify all directory paths are correct
3. Ensure Python 3 and Flask are properly installed
4. Check file permissions on all scripts and directories
5. Review `./logs/activity.log` for user action history
6. Review `./logs/debug_execution.log` for script execution details

## License

This project is licensed under the MIT License.

## Author

© 2026 David Zhorzholiani

---

**simple_Automatica** - Trigger playbooks with confidence
