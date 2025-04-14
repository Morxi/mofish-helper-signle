import win32gui
import win32process
import psutil
import time

class WindowWatcher:
    def __init__(self):
        self.w = win32gui
        
    def get_active_window_title(self):
        return self.w.GetWindowText(self.w.GetForegroundWindow())

    def get_activate_window_hwnd(self):
        return self.w.GetForegroundWindow()
    
    def get_process_info(self):
        """获取当前活动窗口的进程信息 / Get current active window's process information"""
        try:
            # 获取窗口句柄 / Get window handle
            hwnd = self.get_activate_window_hwnd()
            # 获取进程ID / Get process ID
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            # 使用psutil获取进程详细信息 / Use psutil to get process details
            process = psutil.Process(pid)
            return {
                'name': process.name(),
                'exe': process.exe(),
                'cmdline': process.cmdline()
            }
        except Exception as e:
            return {
                'name': None,
                'exe': None,
                'cmdline': None,
                'error': str(e)
            }

if __name__ == "__main__":
    watcher = WindowWatcher()
    while True:
        print("Window Title:", watcher.get_active_window_title())
        print("Window Handle:", watcher.get_activate_window_hwnd())
        process_info = watcher.get_process_info()
        print("Process Name:", process_info['name'])
        print("Process Path:", process_info['exe'])
        print("Command Line:", process_info['cmdline'])
        print("-" * 50)
        time.sleep(1)
