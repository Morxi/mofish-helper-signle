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
        records_to_write = []
        last_window_title = None
        last_process_name = None
        last_write_time = time.time()
        
        while True:
            # Get window information
            window_title = watcher.get_active_window_title()
            process_info = watcher.get_process_info()
            process_name = process_info.get('name')
            current_time = datetime.now().isoformat()
            
            # If window/process changed, add new record
            if window_title != last_window_title or process_name != last_process_name:
                records_to_write.append({
                    'timestamp': current_time,
                    'window_title': window_title,
                    'process_name': process_name,
                    'process_path': process_info.get('exe'),
                    'command_line': str(process_info.get('cmdline'))
                })
                last_window_title = window_title
                last_process_name = process_name
            
            # Write to DB every 10 seconds
            if time.time() - last_write_time >= 10 and records_to_write:
                # Get the last record from DB to check for duplicates
                cursor.execute('''
                    SELECT window_title, process_name, timestamp 
                    FROM window_history 
                    ORDER BY id DESC LIMIT 1
                ''')
                last_db_record = cursor.fetchone()
                
                for record in records_to_write:
                    if last_db_record and \
                       last_db_record[0] == record['window_title'] and \
                       last_db_record[1] == record['process_name']:
                        # Update timestamp of existing record
                        cursor.execute('''
                            UPDATE window_history 
                            SET timestamp = ?
                            WHERE rowid IN (
                                SELECT rowid FROM window_history
                                WHERE window_title = ? AND process_name = ?
                                ORDER BY rowid DESC LIMIT 1
                            )
                        ''', (record['timestamp'], record['window_title'], record['process_name']))
                    else:
                        # Insert new record
                        cursor.execute('''
                            INSERT INTO window_history 
                            (timestamp, window_title, process_name, process_path, command_line)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            record['timestamp'],
                            record['window_title'],
                            record['process_name'],
                            record['process_path'],
                            record['command_line']
                        ))
                
                conn.commit()
                records_to_write = []
                last_write_time = time.time()
            
            # Check every 1 second
            time.sleep(1)
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
