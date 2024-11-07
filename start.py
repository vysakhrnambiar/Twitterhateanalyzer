import subprocess
import time
import random
import signal
import sys
import datetime
import logging
from typing import Optional
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('process_manager.log')
    ]
)

class ProcessManager:
    def __init__(self):
        self.dashboard_process: Optional[subprocess.Popen] = None
        self.current_process: Optional[subprocess.Popen] = None
        self.running = True
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """Set up graceful shutdown handlers"""
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info("\nInitiating graceful shutdown...")
        self.running = False
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Clean up all running processes"""
        processes = [self.dashboard_process, self.current_process]
        for process in processes:
            if process and process.poll() is None:
                logging.info(f"Terminating process {process.pid}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logging.warning(f"Process {process.pid} didn't terminate, forcing...")
                    process.kill()

    def run_process(self, script_name: str) -> bool:
        """Run a Python script and wait for completion"""
        try:
            logging.info(f"Starting {script_name}...")
            self.current_process = subprocess.Popen([sys.executable, script_name])
            self.current_process.wait()
            
            if self.current_process.returncode == 0:
                logging.info(f"{script_name} completed successfully")
                return True
            else:
                logging.error(f"{script_name} failed with return code {self.current_process.returncode}")
                return False
                
        except Exception as e:
            logging.error(f"Error running {script_name}: {e}")
            return False
        finally:
            self.current_process = None

    def run_dashboard(self):
        """Start the dashboard process"""
        try:
            logging.info("Starting dashboard.py...")
            self.dashboard_process = subprocess.Popen([sys.executable, 'dashboard.py'])
            time.sleep(5)  # Give dashboard time to start
            logging.info("Dashboard is running")
        except Exception as e:
            logging.error(f"Error starting dashboard: {e}")
            self.running = False

    def run_sequence(self):
        """Run the sequence of scripts"""
        scripts = ['Gettweets.py', 'screenshots_analyze.py', 'tweet_analyzer.py']
        
        for script in scripts:
            if not self.running:
                break
                
            if not self.run_process(script):
                logging.error(f"Error in sequence at {script}")
                break
            
            if not self.running:
                break

    def get_next_run_time(self) -> datetime.datetime:
        """Generate random time between 1-3 hours from now"""
        minutes = random.randint(60, 180)
        next_run = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        return next_run

    def format_timedelta(self, td: datetime.timedelta) -> str:
        """Format timedelta into a readable string"""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours} hours, {minutes} minutes"

    def wait_until_next_run(self, next_run: datetime.datetime):
        """Wait until next run with 5-minute countdown updates"""
        last_update = datetime.datetime.now()
        update_interval = datetime.timedelta(minutes=5)
        
        while datetime.datetime.now() < next_run and self.running:
            current_time = datetime.datetime.now()
            
            # Update every 5 minutes
            if current_time - last_update >= update_interval:
                time_remaining = next_run - current_time
                logging.info(f"Time until next run: {self.format_timedelta(time_remaining)}")
                last_update = current_time
            
            # Sleep for 30 seconds between checks
            time.sleep(30)

    def run(self):
        """Main execution loop"""
        try:
            # Start dashboard
            self.run_dashboard()
            if not self.running:
                return

            # First immediate run
            logging.info("Starting initial sequence run")
            self.run_sequence()

            # Continue with timed runs
            while self.running:
                next_run = self.get_next_run_time()
                logging.info(f"Next run scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')} "
                           f"({self.format_timedelta(next_run - datetime.datetime.now())} from now)")
                
                # Wait until next run with status updates
                self.wait_until_next_run(next_run)
                
                if self.running:
                    logging.info("Starting scheduled sequence run")
                    self.run_sequence()

        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        finally:
            self.cleanup()

if __name__ == "__main__":
    manager = ProcessManager()
    manager.run()