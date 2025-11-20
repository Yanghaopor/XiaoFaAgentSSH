from typing import Dict, Any, Optional, Callable
import time
import threading

class SimpleSSHExecutor:
    """简化的SSH执行器 - 只负责执行命令并返回结果"""
    
    def __init__(self, ssh_connection, emit_func, ai_processor=None, session_id=None):
        self.ssh_connection = ssh_connection
        self.emit = emit_func
        self.ai_processor = ai_processor
        self.session_id = session_id
        self.is_executing = False
        self.current_session_id = None
    
    def execute_command(self, command: str, session_id: str) -> bool:
        """执行SSH命令"""
        if self.is_executing:
            self.emit('system_message', {
                'message': '系统正在执行其他命令，请稍候...',
                'session_id': session_id
            })
            return False
        
        # 启动执行线程
        thread = threading.Thread(
            target=self._execute_command_thread,
            args=(command, session_id)
        )
        thread.daemon = True
        thread.start()
        return True
    
    def _execute_command_thread(self, command: str, session_id: str):
        """在独立线程中执行SSH命令"""
        try:
            self.is_executing = True
            self.current_session_id = session_id
            
            print(f"[SSH执行器] 开始执行命令: {command}")
            
            # 发送命令开始通知
            self.emit('command_start', {
                'command': command,
                'session_id': session_id
            })
            
            # 执行SSH命令
            output = self.ssh_connection.execute_command(command)
            
            print(f"[SSH执行器] 命令执行完成，输出长度: {len(output) if output else 0}")
            
            # 发送命令输出
            if output:
                self.emit('command_output', {
                    'output': output,
                    'session_id': session_id
                })
            
            # 发送命令完成通知
            self.emit('command_completed', {
                'command': command,
                'output': output or '',
                'session_id': session_id
            })
            
            # 直接调用AI处理器分析结果
            if self.ai_processor:
                self.ai_processor.process_ssh_result(command, output or '', session_id)
            
        except Exception as e:
            error_msg = f"执行SSH命令时发生错误: {str(e)}"
            print(f"[SSH执行器] {error_msg}")
            self.emit('command_error', {
                'error': error_msg,
                'command': command,
                'session_id': session_id
            })
        finally:
            self.is_executing = False
            self.current_session_id = None
    
    def send_input(self, input_text: str, session_id: str) -> bool:
        """向当前SSH会话发送输入"""
        try:
            if not self.ssh_connection:
                return False
            
            print(f"[SSH执行器] 发送输入: {input_text}")
            
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
            print(f"[SSH执行器] {error_msg}")
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
        """停止当前执行（如果可能）"""
        if self.is_executing and self.ssh_connection:
            try:
                # 发送Ctrl+C中断信号
                self.ssh_connection.send_keys('\x03')
                return True
            except Exception as e:
                print(f"[SSH执行器] 停止执行失败: {e}")
                return False
        return False