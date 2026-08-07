import time
import sys
import re

LOG_FILE = "/home/ubuntu/.gemini/antigravity-ide/brain/b0cfee91-04b6-493f-9c72-b48b55ff1eda/.system_generated/tasks/task-881.log"

def main():
    print("=" * 60)
    print("📊 LIVE EVALUATION PROGRESS MONITOR")
    print("=" * 60)
    
    current_progress = 0
    total = 300
    
    # regex pattern to match "[RetrievalEval] [50/300]"
    pattern = re.compile(r"\[RetrievalEval\] \[(\d+)/(\d+)\]")

    try:
        with open(LOG_FILE, "r") as f:
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
        print(f"Log file not found: {LOG_FILE}")

if __name__ == "__main__":
    main()
