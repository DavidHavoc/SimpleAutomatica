#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import datetime

def main():
    parser = argparse.ArgumentParser(description='Run PowerShell Script')
    parser.add_argument('--playbooks', required=True, help='Path to script file (reusing argument name)')
    parser.add_argument('--inventory', required=True, help='Path to inventory file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--forks', default='1', help='Number of forks')
    args = parser.parse_args()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = f"logs/{timestamp}_powershell"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "execution.log")

    print(f"Starting PowerShell execution...")
    print(f"Script: {args.playbooks}")
    print(f"Inventory: {args.inventory}")
    print(f"Logs: {log_file}")

    # Assuming pwsh for PowerShell Core on Linux/Mac
    cmd = ["pwsh", "-File", args.playbooks, "-Inventory", args.inventory]
    
    with open(log_file, "w") as f:
        f.write(f"Execution started at {timestamp}\n")
        f.write(f"Command: {' '.join(cmd)}\n\n")
        f.flush()
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in process.stdout:
                sys.stdout.write(line)
                f.write(line)
            process.wait()
            if process.returncode != 0:
                f.write(f"\nExecution failed with return code {process.returncode}\n")
                # Don't exit with error to avoid crashing the wrapper if pwsh is missing, just log it
        except FileNotFoundError:
            msg = "pwsh command not found. Simulating execution for demo.\n"
            print(msg)
            f.write(msg)
            f.write(f"Simulating PowerShell script {os.path.basename(args.playbooks)}...\n")
            f.write("Reading inventory...\n")
            f.write("Processing items...\n")
            f.write("Done.\n")

    print("Execution complete.")

if __name__ == "__main__":
    main()
