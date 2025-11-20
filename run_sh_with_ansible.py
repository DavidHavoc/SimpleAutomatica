#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import datetime

def main():
    parser = argparse.ArgumentParser(description='Run Shell Script')
    parser.add_argument('--playbooks', required=True, help='Path to script file (reusing playbooks arg)')
    parser.add_argument('--inventory', required=True, help='Path to inventory file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--forks', default='1', help='Number of forks')
    args = parser.parse_args()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = f"logs/{timestamp}_shell"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "execution.log")

    print(f"Starting Shell execution...")
    print(f"Script: {args.playbooks}")
    print(f"Inventory: {args.inventory}")
    print(f"Logs: {log_file}")

    cmd = ["/bin/bash", args.playbooks, args.inventory]
    
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
        except Exception as e:
            msg = f"Error executing shell script: {e}\n"
            print(msg)
            f.write(msg)

    print("Execution complete.")

if __name__ == "__main__":
    main()
