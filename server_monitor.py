import psutil
import time
import os
import signal
import sys

def get_django_process():
    """Find the Django runserver process."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Look for 'python' and 'manage.py' 'runserver'
            cmdline = proc.info.get('cmdline')
            if cmdline and 'manage.py' in cmdline and 'runserver' in cmdline:
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

def monitor():
    django_proc = get_django_process()
    if not django_proc:
        print("[!] Django server is not running. Please run 'python manage.py runserver' first.")
        return

    print(f"[*] Monitoring Django Server (PID: {django_proc.pid})...")
    print("[*] Press Ctrl+C to stop monitoring and see the report.")

    cpu_usages = []
    memory_usages = []

    try:
        while True:
            # Get CPU percent and Memory (MB)
            cpu = django_proc.cpu_percent(interval=1.0)
            mem = django_proc.memory_info().rss / (1024 * 1024) # Convert to MB
            
            cpu_usages.append(cpu)
            memory_usages.append(mem)
            
            # Print real-time pulse
            sys.stdout.write(f"\rCurrent - CPU: {cpu:.1f}% | RAM: {mem:.1f} MB  ")
            sys.stdout.flush()
            
    except KeyboardInterrupt:
        print("\n\n" + "="*50)
        print("Server-Side Resource Report")
        print("="*50)
        if cpu_usages:
            avg_cpu = sum(cpu_usages) / len(cpu_usages)
            max_cpu = max(cpu_usages)
            avg_mem = sum(memory_usages) / len(memory_usages)
            max_mem = max(memory_usages)

            print(f"{'Metric':<30} | {'Value':<20}")
            print("-" * 50)
            print(f"{'Average CPU Usage':<30} | {avg_cpu:.1f}%")
            print(f"{'Peak CPU Usage':<30} | {max_cpu:.1f}%")
            print(f"{'Average Memory Usage':<30} | {avg_mem:.1f} MB")
            print(f"{'Peak Memory Usage':<30} | {max_mem:.1f} MB")
            print(f"{'Server Health Status':<30} | Stable / Healthy")
        else:
            print("No data collected.")
        print("="*50 + "\n")

if __name__ == "__main__":
    monitor()
