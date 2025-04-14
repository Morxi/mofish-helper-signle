from flask import Flask, jsonify, request, send_from_directory
from WindowWatcher import WindowWatcher
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
watcher = WindowWatcher()

def get_db_connection():
    conn = sqlite3.connect('window_history.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/', defaults={'filename': 'index.html'}, methods=['GET'])
def serve_static(filename):
    """提供静态文件服务
    Serve static files
    """
    return send_from_directory('static', filename)


@app.route('/api/current', methods=['GET'])
def get_current_window():
    """获取当前窗口信息
    Get current window information
    """
    window_title = watcher.get_active_window_title()
    process_info = watcher.get_process_info()
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'window_title': window_title,
        'process_name': process_info.get('name'),
        'process_path': process_info.get('exe'),
        'command_line': process_info.get('cmdline')
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    """获取历史记录
    Get history records
    参数：
    - hours: 过去多少小时的记录（默认1小时）
    - limit: 最大返回条数（默认100条）
    Parameters:
    - hours: Records from how many hours ago (default 1 hour)
    - limit: Maximum number of records to return (default 100 records)
    """
    hours = request.args.get('hours', default=1, type=int)
    limit = request.args.get('limit', default=100, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 计算时间范围
    # Calculate time range
    time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    # 查询数据
    # Query data
    cursor.execute('''
        SELECT * FROM window_history 
        WHERE timestamp > ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (time_threshold, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    # 转换为列表
    # Convert to list
    history = [{
        'id': row['id'],
        'timestamp': row['timestamp'],
        'window_title': row['window_title'],
        'process_name': row['process_name'],
        'process_path': row['process_path'],
        'command_line': row['command_line']
    } for row in rows]
    
    return jsonify({
        'total': len(history),
        'hours': hours,
        'items': history
    })

@app.route('/api/screentime', methods=['GET'])
def get_screentime():
    """获取程序使用时间统计
    Get application usage time statistics
    参数：
    - hours: 过去多少小时的记录（默认1小时）
    Parameters:
    - hours: Records from how many hours ago (default 1 hour)
    """
    hours = request.args.get('hours', default=12, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 计算时间范围
    # Calculate time range
    time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    # 获取按时间排序的所有记录
    # Get all records sorted by time
    cursor.execute('''
        SELECT timestamp, window_title, process_name, process_path
        FROM window_history 
        WHERE timestamp > ? 
        ORDER BY timestamp ASC
    ''', (time_threshold,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return jsonify({
            'total_time_seconds': 0,
            'apps': []
        })

    # 初始化数据结构
    # Initialize data structure
    apps_data = defaultdict(lambda: {
        'total_time_seconds': 0,
        'process_name': '',
        'process_path': '',
        'windows': defaultdict(lambda: {
            'total_time_seconds': 0,
            'window_title': ''
        })
    })
    
    # 处理时间序列数据
    # Process time series data
    total_time = 0
    previous_record = None
    
    for current in rows:
        if previous_record is not None:
            # Skip processing if the current record is the same as the previous one
            if (current['process_name'] == previous_record['process_name'] and
                current['window_title'] == previous_record['window_title']):
                continue
        
        # 计算时间差（秒）
        current_time = datetime.fromisoformat(current['timestamp'])
        
        if previous_record is not None:
            next_time = datetime.fromisoformat(previous_record['timestamp'])
            time_diff = (current_time - next_time).total_seconds()
        else:
            time_diff = 0  # No time difference for the first record
        
        # 更新应用程序级别的统计
        process_name = current['process_name']
        window_title = current['window_title']
        
        apps_data[process_name]['total_time_seconds'] += time_diff
        apps_data[process_name]['process_name'] = process_name
        apps_data[process_name]['process_path'] = current['process_path']
        
        # 更新窗口级别的统计
        apps_data[process_name]['windows'][window_title]['total_time_seconds'] += time_diff
        apps_data[process_name]['windows'][window_title]['window_title'] = window_title
        
        total_time += time_diff
        previous_record = current  # Update previous_record to current
    # 转换数据结构为列表格式
    # Convert data structure to list format
    apps_list = []
    for process_name, app_data in apps_data.items():
        # 窗口数据转换为列表并按使用时间排序
        # Convert window data to list and sort by usage time
        windows_list = [
            {
                'window_title': window_data['window_title'],
                'total_time_seconds': round(window_data['total_time_seconds'], 2),
                'total_time_minutes': round(window_data['total_time_seconds'] / 60, 2)
            }
            for window_data in app_data['windows'].values()
        ]
        windows_list.sort(key=lambda x: x['total_time_seconds'], reverse=True)
        
        # 应用程序数据
        # Application data
        apps_list.append({
            'process_name': app_data['process_name'],
            'process_path': app_data['process_path'],
            'total_time_seconds': round(app_data['total_time_seconds'], 2),
            'total_time_minutes': round(app_data['total_time_seconds'] / 60, 2),
            'windows': windows_list
        })
    
    # 按总使用时间排序
    # Sort by total usage time
    apps_list.sort(key=lambda x: x['total_time_seconds'], reverse=True)
    
    return jsonify({
        'total_time_seconds': round(total_time, 2),
        'total_time_minutes': round(total_time / 60, 2),
        'hours_range': hours,
        'apps': apps_list
    }) 