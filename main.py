from WindowWatcher import WindowWatcher
import sqlite3
import time
from datetime import datetime
import threading
from api import app

def init_db():
    conn = sqlite3.connect('window_history.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS window_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        window_title TEXT,
        process_name TEXT,
        process_path TEXT,
        command_line TEXT
    )
    ''')
    conn.commit()
    return conn

def run_data_collection():
    """Run data collection process"""
    watcher = WindowWatcher()
    conn = init_db()
    cursor = conn.cursor()
    
    try:
        while True:
            # Get window information
            window_title = watcher.get_active_window_title()
            process_info = watcher.get_process_info()
            
            # Prepare data
            current_time = datetime.now().isoformat()
            
            # Insert into database
            cursor.execute('''
                INSERT INTO window_history 
                (timestamp, window_title, process_name, process_path, command_line)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                current_time,
                window_title,
                process_info.get('name'),
                process_info.get('exe'),
                str(process_info.get('cmdline'))
            ))
            conn.commit()
            
            # Wait for 5 seconds
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nData collection has been stopped")
    finally:
        conn.close()

def run_api_server():
    """Run API server"""
    app.run(host='0.0.0.0', port=5030)

if __name__ == '__main__':
    # Create data collection thread
    data_thread = threading.Thread(target=run_data_collection)
    data_thread.daemon = True  # Set as a daemon thread, so it will automatically end when the main program exits
    
    # Create API server thread
    api_thread = threading.Thread(target=run_api_server)
    api_thread.daemon = True
    
    try:
        print("Starting data collection service...")
        data_thread.start()
        print("Starting API server (http://localhost:5030)...")
        api_thread.start()
        
        # Keep the main thread running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nProgram is stopping...")
    except Exception as e:
        print(f"An error occurred: {e}")
