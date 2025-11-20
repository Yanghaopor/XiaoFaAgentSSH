from typing import Dict, List, Any, Optional, Callable
import re
import json
import time
import threading
from enum import Enum
from dataclasses import dataclass
import uuid
import os
import pickle

class CommandType(Enum):
    SSH = "ssh"
    ESCAPE = "escape"
    WAIT = "wait"
    DECISION = "decision"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class Task:
    """任务数据结构"""
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: float = None
    started_at: float = None
    completed_at: float = None
    commands: List[str] = None
    result: str = None
    error: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.commands is None:
            self.commands = []

@dataclass
class AgentCommand:
    """代理命令数据结构"""
    type: CommandType
    content: str
    params: Dict[str, Any] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.params is None:
            self.params = {}

class TaskManager:
    """任务管理器"""
    
    def __init__(self, storage_file: str = "tasks.pkl"):
        self.storage_file = storage_file
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []  # 按优先级排序的任务ID列表
        self._load_tasks()
    
    def create_task(self, description: str, priority: TaskPriority = TaskPriority.MEDIUM, 
                   commands: List[str] = None) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            description=description,
            priority=priority,
            commands=commands or []
        )
        self.tasks[task_id] = task
        self._insert_task_by_priority(task_id)
        self._save_tasks()
        return task_id
    
    def _insert_task_by_priority(self, task_id: str):
        """按优先级插入任务到队列"""
        task = self.tasks[task_id]
        priority_order = {
            TaskPriority.URGENT: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3
        }
        
        insert_index = len(self.task_queue)
        for i, existing_task_id in enumerate(self.task_queue):
            existing_task = self.tasks[existing_task_id]
            if priority_order[task.priority] < priority_order[existing_task.priority]:
                insert_index = i
                break
        
        self.task_queue.insert(insert_index, task_id)
    
    def start_task(self, task_id: str) -> bool:
        """开始执行任务"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = time.time()
                self._save_tasks()
                return True
        return False
    
    def complete_task(self, task_id: str, result: str = None) -> bool:
        """完成任务"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == TaskStatus.IN_PROGRESS:
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.result = result
                # 从队列中移除
                if task_id in self.task_queue:
                    self.task_queue.remove(task_id)
                self._save_tasks()
                return True
        return False
    
    def fail_task(self, task_id: str, error: str = None) -> bool:
        """标记任务失败"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == TaskStatus.IN_PROGRESS:
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
                task.error = error
                # 从队列中移除
                if task_id in self.task_queue:
                    self.task_queue.remove(task_id)
                self._save_tasks()
                return True
        return False
    
    def get_next_task(self) -> Optional[Task]:
        """获取下一个待执行的任务"""
        for task_id in self.task_queue:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                return task
        return None
    
    def get_current_task(self) -> Optional[Task]:
        """获取当前正在执行的任务"""
        for task in self.tasks.values():
            if task.status == TaskStatus.IN_PROGRESS:
                return task
        return None
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def get_pending_tasks(self) -> List[Task]:
        """获取待处理任务"""
        return [task for task in self.tasks.values() if task.status == TaskStatus.PENDING]
    
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        completed_task_ids = []
        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                completed_task_ids.append(task_id)
        
        for task_id in completed_task_ids:
            del self.tasks[task_id]
            if task_id in self.task_queue:
                self.task_queue.remove(task_id)
        
        self._save_tasks()
    
    def find_similar_task(self, description: str, commands: List[str] = None) -> Optional[Task]:
        """查找相似的任务"""
        for task in self.tasks.values():
            if task.description == description:
                if commands is None or task.commands == commands:
                    return task
        return None
    
    def has_pending_similar_task(self, description: str, commands: List[str] = None) -> bool:
        """检查是否有相似的待处理任务"""
        similar_task = self.find_similar_task(description, commands)
        return similar_task is not None and similar_task.status == TaskStatus.PENDING
    
    def _save_tasks(self):
        """保存任务到文件"""
        try:
            with open(self.storage_file, 'wb') as f:
                pickle.dump({
                    'tasks': self.tasks,
                    'task_queue': self.task_queue
                }, f)
        except Exception as e:
            print(f"保存任务失败: {e}")
    
    def _load_tasks(self):
        """从文件加载任务"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'rb') as f:
                    data = pickle.load(f)
                    self.tasks = data.get('tasks', {})
                    self.task_queue = data.get('task_queue', [])
                    
                    # 清理无效的队列项
                    self.task_queue = [task_id for task_id in self.task_queue if task_id in self.tasks]
        except Exception as e:
            print(f"加载任务失败: {e}")
            self.tasks = {}
            self.task_queue = []

class CommandParser:
    """命令解析器"""
    
    def __init__(self):
        self.command_patterns = {
            'ssh': r'SSH\{([^}]+)\}',
            'escape': r'EC\{([^}]+)\}',
            'wait': r'WAIT\{([^}]+)\}'
        }
    
    def parse_message(self, message: str) -> List[AgentCommand]:
        """解析消息中的代理命令"""
        commands = []
        
        # 解析SSH命令
        ssh_matches = re.findall(self.command_patterns['ssh'], message)
        for match in ssh_matches:
            commands.append(AgentCommand(
                type=CommandType.SSH,
                content=match.strip()
            ))
        
        # 解析快捷键命令
        escape_matches = re.findall(self.command_patterns['escape'], message)
        for match in escape_matches:
            # 解析按键参数
            keys = [key.strip().strip('"').strip("'") for key in match.split(',')]
            commands.append(AgentCommand(
                type=CommandType.ESCAPE,
                content=f"快捷键: {'+'.join(keys)}",
                params={'keys': keys}
            ))
        
        # 解析等待命令
        wait_matches = re.findall(self.command_patterns['wait'], message)
        for match in wait_matches:
            try:
                seconds = float(match.strip())
            except ValueError:
                seconds = 1.0
            commands.append(AgentCommand(
                type=CommandType.WAIT,
                content=f"等待 {seconds} 秒",
                params={'seconds': seconds}
            ))
        
        return commands
    
    def has_agent_commands(self, message: str) -> bool:
        """检查消息是否包含代理命令"""
        for pattern in self.command_patterns.values():
            if re.search(pattern, message):
                return True
        return False

class InteractionHandler:
    """交互处理器"""
    
    def __init__(self):
        self.interaction_patterns = {
            'yn_question': r'(?i)\b(y/n|yes/no|\(y/n\)|\[y/n\]|continue\s*\?|proceed\s*\?|确认|是否继续)\b',
            'continue': r'(?i)\b(press\s+any\s+key|按任意键|continue|继续|press\s+enter|回车继续)\b',
            'password': r'(?i)\b(password|密码|passwd|输入密码)\s*[:：]?\s*$',
            'confirm': r'(?i)\b(confirm|确认|are\s+you\s+sure|确定要|really\s+want|overwrite|覆盖)\b',
            'download_progress': r'(?i)\b(downloading|下载中|progress|进度|\d+%|\d+/\d+|\[.*\].*\d+%)\b',
            'download_complete': r'(?i)\b(download\s+complete|下载完成|installation\s+complete|安装完成|successfully\s+installed|成功安装)\b',
            'installation_prompt': r'(?i)\b(install|安装|setup|配置|would\s+you\s+like\s+to\s+install)\b.*\?'
        }
    
    def detect_interaction(self, output: str) -> Optional[str]:
        """检测输出中的交互类型"""
        for interaction_type, pattern in self.interaction_patterns.items():
            if re.search(pattern, output):
                return interaction_type
        return None
    
    def generate_response(self, interaction_type: str, context: str) -> str:
        """生成交互响应"""
        responses = {
            'yn_question': 'y\n',
            'continue': '\n',
            'password': '',  # 需要用户输入
            'confirm': 'y\n',
            'download_progress': '',  # 不需要响应，只是监控
            'download_complete': '',  # 不需要响应
            'installation_prompt': 'y\n'  # 默认同意安装
        }
        return responses.get(interaction_type, '')

class SSHAgentExecutor:
    """SSH代理执行器"""
    
    def __init__(self, ssh_connection, ai_client, emit_func):
        self.ssh_connection = ssh_connection
        self.ai_client = ai_client
        self.emit = emit_func
        self.parser = CommandParser()
        self.task_manager = TaskManager()
        self.interaction_handler = InteractionHandler()
        self.is_executing = False
    
    def execute_agent_commands(self, message: str, session_id: str) -> bool:
        """执行代理命令"""
        if self.is_executing:
            print(f"[AI代理] 已有命令正在执行，跳过重复执行")
            self.emit('agent_error', {
                'error': '已有命令正在执行，请等待当前任务完成',
                'session_id': session_id
            })
            return False
        
        commands = self.parser.parse_message(message)
        if not commands:
            return False
        
        # 检查是否有相似的待处理任务
        command_strings = [cmd.content for cmd in commands]
        if self.task_manager.has_pending_similar_task(message, command_strings):
            print(f"[AI代理] 发现相似的待处理任务，跳过重复创建")
            self.emit('ai_thinking', {
                'thinking': '检测到相似的待处理任务，避免重复执行',
                'session_id': session_id
            })
            return False
        
        # 创建新任务
        task_id = self.task_manager.create_task(
            description=message,
            commands=command_strings
        )
        
        # 发送任务创建通知
        self.emit('task_created', {
            'task_id': task_id,
            'description': message,
            'commands_count': len(commands),
            'session_id': session_id
        })
        
        # 在新线程中执行命令
        thread = threading.Thread(
            target=self._execute_commands_thread,
            args=(commands, session_id, task_id)
        )
        thread.daemon = True
        thread.start()
        
        return True
    
    def _execute_commands_thread(self, commands: List[AgentCommand], session_id: str, task_id: str):
        """在线程中执行命令"""
        try:
            self.is_executing = True
            
            # 开始任务
            if not self.task_manager.start_task(task_id):
                self.emit('agent_error', {
                    'error': f'无法开始任务 {task_id}',
                    'session_id': session_id
                })
                return
            
            print(f"[AI代理] 开始执行 {len(commands)} 个命令")
            
            for i, command in enumerate(commands):
                print(f"[AI代理] 执行命令 {i+1}/{len(commands)}: {command.type.value} - {command.content}")
                
                if command.type == CommandType.SSH:
                    self._execute_ssh_command(command, session_id)
                elif command.type == CommandType.ESCAPE:
                    self._execute_escape_command(command, session_id)
                elif command.type == CommandType.WAIT:
                    self._execute_wait_command(command)
                
                # 短暂延迟
                time.sleep(0.5)
            
            # 完成任务
            self.task_manager.complete_task(task_id, "所有命令执行完成")
            self.emit('task_completed', {
                'task_id': task_id,
                'session_id': session_id
            })
            
            # 发送执行完成的总结
            self.emit('ai_analysis', {
                'analysis': f'✅ AI代理任务执行完成\n\n已成功执行 {len(commands)} 个命令：\n' + 
                           '\n'.join([f'• {cmd.content}' for cmd in commands[:5]]) + 
                           (f'\n... 还有 {len(commands)-5} 个命令' if len(commands) > 5 else ''),
                'session_id': session_id
            })
            
            print(f"[AI代理] 所有命令执行完成")
            
        except Exception as e:
            print(f"[AI代理] 命令执行失败: {e}")
            self.task_manager.fail_task(task_id, str(e))
            self.emit('agent_error', {
                'error': f'命令执行失败: {str(e)}',
                'session_id': session_id
            })
        finally:
            self.is_executing = False
    
    def _monitor_download_progress(self, command: str, session_id: str, interaction_handler: 'InteractionHandler'):
        """监控下载进度"""
        print(f"[AI代理] 开始监控下载进度")
        
        # 发送AI思考状态
        self.emit('ai_thinking', {
            'thinking': '正在监控下载进度，请稍候...',
            'session_id': session_id
        })
        
        timeout = 300  # 5分钟超时
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            time.sleep(2)  # 每2秒检查一次
            
            # 获取最新输出
            latest_output = self.ssh_connection.get_latest_output()
            if latest_output:
                # 发送输出到前端
                self.emit('command_output', {
                    'output': latest_output,
                    'session_id': session_id
                })
                
                # 检测下载完成或新的交互类型
                interaction_type = interaction_handler.detect_interaction(latest_output)
                if interaction_type == 'download_complete':
                    self.emit('ai_analysis', {
                        'analysis': '下载已完成',
                        'session_id': session_id
                    })
                    return
                elif interaction_type and interaction_type != 'download_progress':
                    # 检测到其他交互类型，处理它
                    self._handle_interaction(interaction_type, latest_output, session_id, interaction_handler)
                    return
        
        # 超时警告
        print(f"[AI代理] 下载监控超时")
        self.emit('ai_analysis', {
            'analysis': '下载监控超时，请检查下载状态',
            'session_id': session_id
        })
    
    def _handle_interaction(self, interaction_type: str, output: str, session_id: str, interaction_handler: 'InteractionHandler'):
        """通用交互处理方法"""
        print(f"[AI代理] 检测到交互场景: {interaction_type}")
        
        # 构建交互提示
        interaction_prompt = f"""检测到SSH命令执行后需要交互响应：

输出: {output}
交互类型: {interaction_type}

请分析这个交互场景并决定如何响应：
1. 如果是Y/N问题，请分析上下文决定选择Y还是N，并使用EC{{"y","enter"}}或EC{{"n","enter"}}格式发送响应
2. 如果是确认操作，请根据命令意图决定是否确认，使用EC{{"y","enter"}}或EC{{"n","enter"}}
3. 如果是密码输入，请说明需要用户提供密码
4. 如果是按任意键继续，使用EC{{"enter"}}继续

请直接给出你的决策和操作。"""
        
        # 发送AI思考状态
        self.emit('ai_thinking', {
            'thinking': f"检测到{interaction_type}交互场景，正在智能处理...",
            'session_id': session_id
        })
        
        if self.ai_client:
            try:
                # 获取AI决策
                ai_decision = self.ai_client.chat(interaction_prompt, "你是一个智能SSH交互处理助手，能够根据上下文智能处理各种交互场景。")
                
                # 发送AI决策结果
                self.emit('ai_decision', {
                    'decision': f"交互处理决策: {ai_decision[:100]}{'...' if len(ai_decision) > 100 else ''}",
                    'session_id': session_id
                })
                
                self.emit('ai_analysis', {
                    'analysis': ai_decision,
                    'session_id': session_id
                })
                
                # 检查AI决策中是否包含代理命令
                if self.parser.has_agent_commands(ai_decision):
                    print(f"[AI代理] AI交互决策包含代理命令，直接执行交互响应")
                    self.emit('ai_thinking', {
                        'thinking': "执行交互响应操作...",
                        'session_id': session_id
                    })
                    
                    interaction_commands = self.parser.parse_message(ai_decision)
                    for cmd in interaction_commands:
                        if cmd.type == CommandType.ESCAPE:
                            self._execute_escape_command(cmd, session_id)
                        elif cmd.type == CommandType.SSH:
                            print(f"[AI代理] 警告：交互处理中不应包含SSH命令，跳过: {cmd.content}")
                        elif cmd.type == CommandType.WAIT:
                            self._execute_wait_command(cmd)
                    
                    # 获取交互响应后的输出
                    time.sleep(1)
                    follow_up_output = self.ssh_connection.get_latest_output()
                    if follow_up_output and follow_up_output.strip():
                        self.emit('command_output', {
                            'output': follow_up_output,
                            'session_id': session_id
                        })
                        
                        # 检测新的交互场景
                        new_interaction = interaction_handler.detect_interaction(follow_up_output)
                        if new_interaction:
                            print(f"[AI代理] 检测到后续交互场景: {new_interaction}")
                            self._handle_interaction(new_interaction, follow_up_output, session_id, interaction_handler)
                            return
                    return
                
            except Exception as e:
                print(f"[AI代理] AI交互处理失败: {e}")
                # 使用默认响应
                default_response = interaction_handler.generate_response(interaction_type, output)
                if default_response:
                    print(f"[AI代理] 使用默认交互响应: {default_response}")
                    response_output = self.ssh_connection.send_keys(default_response)
                    self.emit('command_output', {
                        'output': f"[AI自动响应] {default_response.strip()}\n{response_output if response_output else ''}",
                        'session_id': session_id
                    })
                    self.emit('ai_analysis', {
                        'analysis': f"检测到{interaction_type}交互，已自动响应: {default_response.strip()}",
                        'session_id': session_id
                    })
                    return
        else:
            # 没有AI客户端，使用默认响应
            default_response = interaction_handler.generate_response(interaction_type, output)
            if default_response:
                print(f"[AI代理] 使用默认交互响应: {default_response}")
                response_output = self.ssh_connection.send_keys(default_response)
                self.emit('command_output', {
                    'output': f"[AI自动响应] {default_response.strip()}\n{response_output if response_output else ''}",
                    'session_id': session_id
                })
                self.emit('ai_analysis', {
                    'analysis': f"检测到{interaction_type}交互，已自动响应: {default_response.strip()}",
                    'session_id': session_id
                })
                return
    
    def _execute_ssh_command(self, command: AgentCommand, session_id: str):
        """执行SSH命令"""
        try:
            print(f"[AI代理] 开始执行SSH命令: {command.content}")
            
            # 发送命令开始通知
            self.emit('agent_command_start', {
                'command': command.content,
                'type': 'ssh',
                'session_id': session_id
            })
            
            # 执行SSH命令
            output = self.ssh_connection.execute_command(command.content)
            print(f"[AI代理] SSH命令执行完成，输出长度: {len(output) if output else 0}")
            
            # 发送命令输出
            if output:
                self.emit('command_output', {
                    'output': output,
                    'session_id': session_id
                })
            
            # 检测交互场景
            interaction_handler = self.interaction_handler
            interaction_type = interaction_handler.detect_interaction(output)
            
            if interaction_type:
                # 特殊处理下载进度
                if interaction_type == 'download_progress':
                    self._monitor_download_progress(command.content, session_id, interaction_handler)
                    return
                
                # 使用通用交互处理方法
                self._handle_interaction(interaction_type, output, session_id, interaction_handler)
                return
            
            # 如果没有交互需求，命令执行完成
            print(f"[AI代理] SSH命令执行完成，无需交互")
            
            # 发送命令执行完成的分析
            self.emit('ai_analysis', {
                'analysis': f'✅ SSH命令执行完成: {command.content}\n\n输出长度: {len(output) if output else 0} 字符',
                'session_id': session_id
            })
            
        except Exception as e:
            error_msg = f"执行SSH命令时发生错误: {str(e)}"
            print(f"[AI代理] {error_msg}")
            self.emit('agent_error', {
                'error': error_msg,
                'session_id': session_id
            })
    
    def _execute_escape_command(self, command: AgentCommand, session_id: str):
        """执行快捷键命令"""
        try:
            print(f"[AI代理] 开始执行快捷键命令: {command.content}")
            
            # 获取按键参数
            keys = command.params.get('keys', []) if command.params else []
            
            if not keys:
                print(f"[AI代理] 快捷键命令参数为空")
                return
            
            # 转换按键为序列
            key_sequence = self._convert_keys_to_sequence(keys)
            print(f"[AI代理] 转换后的按键序列: {key_sequence}")
            
            # 在SSH终端界面显示AI代理正在执行的快捷键
            self.emit('command_output', {
                'output': f"\n[AI代理按键] {' + '.join(keys)}\n",
                'session_id': session_id
            })
            
            # 发送快捷键到SSH连接
            output = self.ssh_connection.send_keys(key_sequence)
            print(f"[AI代理] 快捷键执行完成，输出长度: {len(output) if output else 0}")
            
            # 在SSH终端界面显示快捷键执行结果
            if output:
                self.emit('command_output', {
                    'output': output,
                    'session_id': session_id
                })
            
        except Exception as e:
            error_msg = f"执行快捷键命令时发生错误: {str(e)}"
            print(f"[AI代理] {error_msg}")
            self.emit('agent_error', {
                'error': error_msg,
                'session_id': session_id
            })
    
    def _execute_wait_command(self, command: AgentCommand):
        """执行等待命令"""
        wait_time = command.params.get('seconds', 1) if command.params else 1
        print(f"[AI代理] 等待 {wait_time} 秒")
        time.sleep(wait_time)
    
    def _convert_keys_to_sequence(self, keys: List[str]) -> str:
        """将按键列表转换为SSH可识别的按键序列"""
        key_mapping = {
            'enter': '\r',
            'tab': '\t',
            'space': ' ',
            'ctrl+c': '\x03',
            'ctrl+d': '\x04',
            'ctrl+z': '\x1a',
            'escape': '\x1b',
            'backspace': '\x08',
            'delete': '\x7f'
        }
        
        sequence = ''
        for key in keys:
            key_lower = key.lower().strip()
            if key_lower in key_mapping:
                sequence += key_mapping[key_lower]
            else:
                # 普通字符直接添加
                sequence += key
        
        return sequence
    
    def get_execution_status(self) -> Dict[str, Any]:
        """获取执行状态"""
        current_task = self.task_manager.get_current_task()
        return {
            'is_executing': self.is_executing,
            'current_task': {
                'id': current_task.id,
                'description': current_task.description,
                'status': current_task.status.value,
                'priority': current_task.priority.value,
                'created_at': current_task.created_at,
                'started_at': current_task.started_at
            } if current_task else None,
            'pending_tasks_count': len(self.task_manager.get_pending_tasks()),
            'total_tasks_count': len(self.task_manager.get_all_tasks())
        }
    
    def get_task_list(self) -> List[Dict[str, Any]]:
        """获取任务列表"""
        tasks = self.task_manager.get_all_tasks()
        return [{
            'id': task.id,
            'description': task.description,
            'status': task.status.value,
            'priority': task.priority.value,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'commands': task.commands,
            'result': task.result,
            'error': task.error
        } for task in tasks]
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取任务详情"""
        task = None
        for t in self.task_manager.get_all_tasks():
            if t.id == task_id:
                task = t
                break
        
        if task:
            return {
                'id': task.id,
                'description': task.description,
                'status': task.status.value,
                'priority': task.priority.value,
                'created_at': task.created_at,
                'started_at': task.started_at,
                'completed_at': task.completed_at,
                'commands': task.commands,
                'result': task.result,
                'error': task.error
            }
        return None
    
    def clear_completed_tasks(self) -> int:
        """清理已完成的任务"""
        before_count = len(self.task_manager.get_all_tasks())
        self.task_manager.clear_completed_tasks()
        after_count = len(self.task_manager.get_all_tasks())
        return before_count - after_count