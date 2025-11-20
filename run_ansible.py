#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import datetime
import shutil # Added import for shutil

def main():
    parser = argparse.ArgumentParser(description='Run Ansible Playbook')
    parser.add_argument('--playbooks', required=True, help='Path to playbook file')
    parser.add_argument('--inventory', required=True, help='Path to inventory file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output') # Added verbose argument
    parser.add_argument('--forks', default='1', help='Number of forks') # Added forks argument
    args = parser.parse_args()

    # Create logs directory if it doesn't exist
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_dir = os.path.join('logs', f"{timestamp}_ansible")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'execution.log')

    print("Starting Ansible execution...")
    print(f"Playbook: {args.playbooks}")
    print(f"Inventory: {args.inventory}")
    print(f"Logs: {log_file}")
    with open(log_file, 'w') as f:
        f.write(f"Execution started at {timestamp}\n")
        # Construct the ansible-playbook command
        cmd = [
            'ansible-playbook',
            args.playbooks,
            '-i', args.inventory,
            '--forks', args.forks
        ]
        if args.verbose:
            cmd.append('-vvv') # Add verbose flag if enabled

        f.write(f"Command: {' '.join(cmd)}\n\n")
        f.flush()
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            for line in process.stdout:
                sys.stdout.write(line)
                f.write(line)
                
            process.wait()
            if process.returncode != 0:
                f.write(f"\nExecution failed with return code {process.returncode}\n")
                sys.exit(process.returncode)
                
        except Exception as e:
            msg = f"Error executing command: {str(e)}\n"
            print(msg)
            f.write(msg)
            sys.exit(1)

    print("Execution complete.")

if __name__ == "__main__":
    main()
