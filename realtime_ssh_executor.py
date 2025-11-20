import paramiko
import threading
import time
import re
from typing import Callable, Dict, Any

class RealtimeSSHExecutor:
    """实时SSH执行器，支持流式输出和下载进度监控"""
    
    def __init__(self, emit_func: Callable):
        self.emit = emit_func
        self.ssh_connection = None
        self.ai_processor = None
        self.is_executing = False
        self.current_session_id = None
        self.monitoring_thread = None
        self.stop_monitoring = False
        
    def set_ssh_connection(self, ssh_connection):
        """设置SSH连接"""
        self.ssh_connection = ssh_connection
        
    def set_ai_processor(self, ai_processor):
        """设置AI处理器"""
        self.ai_processor = ai_processor
        
    def execute_command(self, command: str, session_id: str) -> bool:
        """执行SSH命令，支持实时输出"""
        if self.is_executing:
            self.emit('system_message', {
                'message': '系统正在执行其他命令，请稍候...',
                'session_id': session_id
            })
            return False
        
        # 启动执行线程
        thread = threading.Thread(
            target=self._execute_command_realtime,
            args=(command, session_id)
        )
        thread.daemon = True
        thread.start()
        return True
        
    def _execute_command_realtime(self, command: str, session_id: str):
        """实时执行SSH命令"""
        try:
            self.is_executing = True
            self.current_session_id = session_id
            self.stop_monitoring = False
            
            print(f"[实时SSH执行器] 开始执行命令: {command}")
            
            # 发送命令开始通知
            self.emit('command_start', {
                'command': command,
                'session_id': session_id
            })
            
            if not self.ssh_connection or not self.ssh_connection.connected:
                raise Exception("SSH连接未建立")
                
            # 发送命令
            shell = self.ssh_connection.shell
            shell.send(command.encode('utf-8') + b'\n')
            
            # 检测是否为下载命令
            is_download_command = self._is_download_command(command)
            
            if is_download_command:
                # 启动下载进度监控
                self._start_download_monitoring(command, session_id)
            
            # 实时读取输出
            full_output = ""
            last_output_time = time.time()
            
            while True:
                if shell.recv_ready():
                    data = shell.recv(1024)
                    try:
                        output_chunk = data.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            output_chunk = data.decode('gbk')
                        except UnicodeDecodeError:
                            output_chunk = data.decode('latin-1')
                    
                    if output_chunk:
                        # 清理ANSI转义序列
                        clean_chunk = self.ssh_connection._clean_ansi_codes(output_chunk)
                        full_output += clean_chunk
                        
                        # 实时发送输出
                        self.emit('command_output', {
                            'output': clean_chunk,
                            'session_id': session_id
                        })
                        
                        last_output_time = time.time()
                        
                        # 检测下载进度
                        if is_download_command:
                            self._check_download_progress(clean_chunk, session_id)
                
                # 检查是否超时（5秒无输出认为命令完成）
                if time.time() - last_output_time > 5:
                    break
                    
                time.sleep(0.1)
            
            # 停止监控
            self.stop_monitoring = True
            
            print(f"[实时SSH执行器] 命令执行完成，总输出长度: {len(full_output)}")
            
            # 发送命令完成通知
            self.emit('command_completed', {
                'command': command,
                'output': full_output,
                'session_id': session_id
            })
            
            # 调用AI处理器分析结果
            if self.ai_processor:
                self.ai_processor.process_ssh_result(command, full_output, session_id)
                
        except Exception as e:
            error_msg = f"执行SSH命令时发生错误: {str(e)}"
            print(f"[实时SSH执行器] {error_msg}")
            self.emit('command_error', {
                'error': error_msg,
                'command': command,
                'session_id': session_id
            })
        finally:
            self.is_executing = False
            self.current_session_id = None
            self.stop_monitoring = True
            
    def _is_download_command(self, command: str) -> bool:
        """检测是否为下载命令"""
        download_patterns = [
            r'curl.*-o',
            r'wget',
            r'apt.*install',
            r'yum.*install',
            r'npm.*install',
            r'pip.*install',
            r'setup_\d+\.x.*bash'
        ]
        
        for pattern in download_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False
        
    def _start_download_monitoring(self, command: str, session_id: str):
        """启动下载进度监控"""
        self.monitoring_thread = threading.Thread(
            target=self._monitor_download_progress,
            args=(command, session_id)
        )
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
    def _monitor_download_progress(self, command: str, session_id: str):
        """监控下载进度"""
        print(f"[下载监控] 开始监控下载进度: {command}")
        
        while not self.stop_monitoring:
            time.sleep(1)
            
            # 发送监控状态
            self.emit('download_monitoring', {
                'command': command,
                'status': 'monitoring',
                'session_id': session_id
            })
            
    def _check_download_progress(self, output_chunk: str, session_id: str):
        """检查下载进度"""
        # 检测各种进度模式
        progress_patterns = [
            r'(\d+)%',  # 百分比进度
            r'\[(#+)\s*\]',  # 进度条
            r'(\d+)/(\d+)',  # 分数进度
            r'Downloaded\s+(\d+)%',  # 下载百分比
            r'Progress:\s*(\d+)%'  # 进度百分比
        ]
        
        for pattern in progress_patterns:
            matches = re.findall(pattern, output_chunk)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        # 处理元组匹配（如进度条）
                        if len(match) == 2 and match[1].isdigit():
                            # 分数进度
                            current = int(match[0])
                            total = int(match[1])
                            progress = int((current / total) * 100)
                        else:
                            continue
                    else:
                        # 处理单个匹配（如百分比）
                        if match.isdigit():
                            progress = int(match)
                        else:
                            continue
                    
                    # 发送进度更新
                    self.emit('download_progress', {
                        'progress': progress,
                        'session_id': session_id
                    })
                    
                    # 检查是否完成
                    if progress >= 100:
                        self._notify_download_complete(session_id)
                        
    def _notify_download_complete(self, session_id: str):
        """通知下载完成"""
        print(f"[下载监控] 检测到下载完成")
        
        # 发送下载完成通知
        self.emit('download_complete', {
            'message': '下载已完成 (100%)',
            'session_id': session_id
        })
        
        # 通知AI下载完成
        if self.ai_processor:
            self.ai_processor.process_user_message(
                "下载已完成，请继续下一步操作", 
                session_id
            )
            
    def send_input(self, input_text: str, session_id: str) -> bool:
        """向当前SSH会话发送输入"""
        try:
            if not self.ssh_connection:
                return False
            
            print(f"[实时SSH执行器] 发送输入: {input_text}")
            
            # 发送输入到SSH连接
            output = self.ssh_connection.send_keys(input_text)
            
            # 发送输出到前端
            if output:
                self.emit('command_output', {
                    'output': output,
                    'session_id': session_id
                })
            
            return True
            
        except Exception as e:
            error_msg = f"发送输入时发生错误: {str(e)}"
            print(f"[实时SSH执行器] {error_msg}")
            self.emit('command_error', {
                'error': error_msg,
                'session_id': session_id
            })
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """获取执行状态"""
        return {
            'is_executing': self.is_executing,
            'current_session_id': self.current_session_id
        }
        
    def stop_execution(self) -> bool:
        """停止当前执行"""
        if self.is_executing and self.ssh_connection:
            try:
                # 发送Ctrl+C中断信号
                self.ssh_connection.send_keys('\x03')
                self.stop_monitoring = True
                return True
            except Exception as e:
                print(f"[实时SSH执行器] 停止执行失败: {e}")
                return False
        return False