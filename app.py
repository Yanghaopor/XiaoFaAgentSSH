from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import paramiko
import threading
import time
import json
from qwen_api.qwen_client import QwenClient
from realtime_ssh_executor import RealtimeSSHExecutor
from ai_processor import AIProcessor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ssh_web_terminal_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量
ssh_connections = {}
ai_processors = {}

# 初始化千问客户端
try:
    qwen_client = QwenClient()
except Exception as e:
    print(f"千问客户端初始化失败: {e}")
    qwen_client = None

class SSHConnection:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None
        self.shell = None
        self.connected = False
    
    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(self.host, port=self.port, username=self.username, password=self.password)
            self.shell = self.client.invoke_shell(term='xterm', width=80, height=24)
            
            # 设置终端编码为UTF-8
            self.shell.send(b'export LANG=en_US.UTF-8\n')
            self.shell.send(b'export LC_ALL=en_US.UTF-8\n')
            time.sleep(0.2)
            
            # 清空初始输出
            while self.shell.recv_ready():
                self.shell.recv(1024)
            
            self.connected = True
            return True
        except Exception as e:
            print(f"SSH连接失败: {e}")
            return False
    
    def execute_command(self, command):
        if not self.connected or not self.shell:
            return "SSH连接未建立"
        
        try:
            self.shell.send(command.encode('utf-8') + b'\n')
            time.sleep(0.5)  # 等待命令执行
            
            output = ""
            while self.shell.recv_ready():
                data = self.shell.recv(1024)
                try:
                    # 尝试多种编码方式
                    output += data.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        output += data.decode('gbk')
                    except UnicodeDecodeError:
                        output += data.decode('latin-1')
            
            # 清理ANSI转义序列和控制字符
            output = self._clean_ansi_codes(output)
            return output
        except Exception as e:
            return f"命令执行失败: {e}"
    
    def send_keys(self, key_sequence):
        """发送快捷键序列"""
        if not self.connected or not self.shell:
            return "SSH连接未建立"
        
        try:
            if isinstance(key_sequence, str):
                self.shell.send(key_sequence.encode('utf-8'))
            else:
                self.shell.send(key_sequence)
            
            time.sleep(0.3)  # 等待响应
            
            output = ""
            while self.shell.recv_ready():
                data = self.shell.recv(1024)
                try:
                    output += data.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        output += data.decode('gbk')
                    except UnicodeDecodeError:
                        output += data.decode('latin-1')
            
            return self._clean_ansi_codes(output)
        except Exception as e:
            return f"发送按键失败: {e}"
    
    def get_latest_output(self):
        """获取最新输出"""
        if not self.connected or not self.shell:
            return ""
        
        try:
            output = ""
            while self.shell.recv_ready():
                data = self.shell.recv(1024)
                try:
                    output += data.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        output += data.decode('gbk')
                    except UnicodeDecodeError:
                        output += data.decode('latin-1')
            
            return self._clean_ansi_codes(output)
        except Exception as e:
            return f"获取输出失败: {e}"
    
    def _clean_ansi_codes(self, text):
        """清理ANSI转义序列"""
        import re
        # 移除ANSI转义序列
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', text)
        
        # 移除其他控制字符，但保留换行符和制表符
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
        
        return cleaned
    
    def disconnect(self):
        if self.client:
            self.client.close()
        self.connected = False

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/connect', methods=['POST'])
def connect_ssh():
    host = request.form['host']
    port = int(request.form['port'])
    username = request.form['username']
    password = request.form['password']
    
    ssh_conn = SSHConnection(host, port, username, password)
    
    if ssh_conn.connect():
        session_id = request.remote_addr + str(time.time())
        ssh_connections[session_id] = ssh_conn
        session['session_id'] = session_id
        session['ssh_info'] = {
            'host': host,
            'port': port,
            'username': username
        }
        
        # 创建实时SSH执行器和AI处理器
        def emit_func(event, data):
            socketio.emit(event, data)
        
        ssh_executor = RealtimeSSHExecutor(emit_func)
        ssh_executor.set_ssh_connection(ssh_conn)
        
        ai_processor = AIProcessor(qwen_client, None, emit_func)
        ai_processor.set_ssh_executor(ssh_executor)
        ssh_executor.set_ai_processor(ai_processor)
        ai_processors[session_id] = ai_processor
        
        # 延迟触发系统信息收集（确保SSH连接完全建立）
        def delayed_system_info_collection():
            time.sleep(2)  # 等待2秒确保连接稳定
            try:
                print(f"[应用] 开始为会话 {session_id} 收集系统信息...")
                ai_processor._collect_system_info_if_needed()
                print(f"[应用] 会话 {session_id} 系统信息收集完成")
            except Exception as e:
                print(f"[应用] 系统信息收集失败: {e}")
        
        # 在后台线程中执行系统信息收集
        threading.Thread(target=delayed_system_info_collection, daemon=True).start()
        
        return redirect(url_for('terminal'))
    else:
        return render_template('login.html', error='SSH连接失败，请检查连接信息')

@app.route('/terminal')
def terminal():
    if 'session_id' not in session:
        return redirect(url_for('index'))
    return render_template('terminal.html')

@socketio.on('execute_command')
def handle_command(data):
    session_id = data.get('session_id')
    command = data.get('command')
    
    if session_id in ssh_connections:
        ssh_conn = ssh_connections[session_id]
        
        try:
            output = ssh_conn.execute_command(command)
            emit('command_output', {
                'output': output,
                'session_id': session_id
            })
        except Exception as e:
            emit('command_error', {
                'error': f'命令执行失败: {str(e)}',
                'session_id': session_id
            })
    else:
        emit('command_error', {
            'error': 'SSH连接不存在',
            'session_id': session_id
        })

@socketio.on('ai_question')
def handle_ai_question(data):
    session_id = data.get('session_id')
    question = data.get('question')
    
    if session_id in ai_processors:
        ai_processor = ai_processors[session_id]
        ai_processor.process_user_message(question, session_id)
    else:
        emit('ai_error', {
            'error': 'AI处理器不存在',
            'session_id': session_id
        })

@socketio.on('user_input')
def handle_user_input(data):
    """处理用户输入（如密码、确认等）"""
    session_id = data.get('session_id')
    user_input = data.get('input')
    
    if session_id in ai_processors:
        ai_processor = ai_processors[session_id]
        ai_processor.handle_user_input(user_input, session_id)
    else:
        emit('ai_error', {
            'error': 'AI处理器不存在',
            'session_id': session_id
        })

@socketio.on('command_completed')
def handle_command_completed(data):
    """处理SSH命令完成事件"""
    session_id = data.get('session_id')
    command = data.get('command')
    output = data.get('output')
    
    if session_id in ai_processors:
        ai_processor = ai_processors[session_id]
        ai_processor.process_ssh_result(command, output, session_id)

@socketio.on('disconnect_ssh')
def handle_disconnect():
    session_id = session.get('session_id')
    if session_id:
        if session_id in ssh_connections:
            ssh_connections[session_id].disconnect()
            del ssh_connections[session_id]
        
        if session_id in ai_processors:
            del ai_processors[session_id]
        
        session.pop('session_id', None)
        emit('disconnected', {'message': 'SSH连接已断开'})

@socketio.on('get_status')
def handle_get_status():
    """获取系统状态"""
    session_id = session.get('session_id')
    if session_id and session_id in ai_processors:
        ai_processor = ai_processors[session_id]
        status = ai_processor.get_status()
        emit('status_update', {
            'status': status,
            'session_id': session_id
        })
    else:
        emit('status_update', {
            'status': {'error': '会话不存在'},
            'session_id': session_id
        })

@socketio.on('connect')
def handle_connect():
    session_id = session.get('session_id')
    if session_id:
        emit('connected', {
            'message': '已连接到服务器',
            'session_id': session_id
        })

@socketio.on('disconnect')
def handle_disconnect_event():
    session_id = session.get('session_id')
    if session_id:
        print(f'客户端断开连接: {session_id}')
        if session_id in ssh_connections:
            ssh_connections[session_id].disconnect()
            del ssh_connections[session_id]
        
        if session_id in ai_processors:
            del ai_processors[session_id]

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)