import time
import sys
import re

import os
import glob

def get_latest_log():
    log_dir = "/home/ubuntu/.gemini/antigravity-ide/brain/*/.system_generated/tasks/*.log"
    logs = glob.glob(log_dir)
    if not logs:
        return None
    return max(logs, key=os.path.getctime)

def main():
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        log_file = get_latest_log()
    
    if not log_file:
        print("No log file found.")
        return
        
    print(f"Monitoring log: {log_file}")
    print("=" * 60)
    print("📊 LIVE EVALUATION PROGRESS MONITOR")
    print("=" * 60)
    
    current_progress = 0
    total = 300
    
    # regex pattern to match "[RetrievalEval] [50/300]"
    pattern = re.compile(r"\[RetrievalEval\] \[(\d+)/(\d+)\]")

    try:
        with open(log_file, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    time.sleep(1)
                    continue
                
                match = pattern.search(line)
                if match:
                    current_progress = int(match.group(1))
                    total = int(match.group(2))
                    
                    # Draw progress bar
                    percent = current_progress / total
                    bar_length = 40
                    filled = int(percent * bar_length)
                    bar = "█" * filled + "-" * (bar_length - filled)
                    
                    sys.stdout.write(f"\rProgress: [{bar}] {current_progress}/{total} ({percent:.1%})")
                    sys.stdout.flush()
                    
                if "Evaluation complete" in line:
                    sys.stdout.write("\n\n✅ Evaluation Complete!\n")
                    break
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
    except FileNotFoundError:
        print(f"Log file not found: {log_file}")

if __name__ == "__main__":
    main()
