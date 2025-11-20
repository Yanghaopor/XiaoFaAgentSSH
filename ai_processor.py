from typing import Dict, Any, Optional
import re
import json
import time
from datetime import datetime
from advanced_ai_prompts import AdvancedAIPrompts, PromptContext, TaskType, ContextLevel
from system_info_collector import SystemInfoCollector

class AIProcessor:
    """简化的AI处理器 - 单一AI处理所有任务"""
    
    def __init__(self, ai_client, ssh_executor, emit_func):
        self.ai_client = ai_client
        self.ssh_executor = ssh_executor
        self.emit = emit_func
        self.conversation_history = []
        self.max_history = 10  # 保留最近10轮对话
        
        # 初始化高级提示词系统
        self.advanced_prompts = AdvancedAIPrompts()
        self.user_expertise = "intermediate"  # 默认中级用户
        self.system_info = {}
        self.error_history = []
        self.success_patterns = []
        self.recent_commands = []
        
        # 初始化系统信息收集器
        self.system_info_collector = SystemInfoCollector()
        self.system_info_collected = False
    
    def set_ssh_executor(self, ssh_executor):
        """设置SSH执行器"""
        self.ssh_executor = ssh_executor
        # 当SSH连接建立时，自动收集系统信息
        self._collect_system_info_if_needed()
    
    def process_user_message(self, message: str, session_id: str) -> bool:
        """处理用户消息"""
        try:
            print(f"[AI处理器] 收到用户消息: {message}")
            
            # 添加到对话历史
            self.conversation_history.append({
                'role': 'user',
                'content': message,
                'timestamp': time.time()
            })
            
            # 发送AI思考状态
            self.emit('ai_thinking', {
                'thinking': '正在分析您的请求...',
                'session_id': session_id
            })
            
            # 构建AI提示
            ai_prompt = self._build_ai_prompt(message)
            
            # 获取AI响应
            ai_response = self.ai_client.chat(ai_prompt, self._get_system_prompt())
            
            print(f"[AI处理器] AI响应: {ai_response[:100]}...")
            
            # 添加AI响应到历史
            self.conversation_history.append({
                'role': 'assistant',
                'content': ai_response,
                'timestamp': time.time()
            })
            
            # 清理历史记录
            self._cleanup_history()
            
            # 解析AI响应并执行
            self._parse_and_execute_ai_response(ai_response, session_id)
            
            return True
            
        except Exception as e:
            error_msg = f"处理用户消息时发生错误: {str(e)}"
            print(f"[AI处理器] {error_msg}")
            self.emit('ai_error', {
                'error': error_msg,
                'session_id': session_id
            })
            return False
    
    def process_ssh_result(self, command: str, output: str, session_id: str):
        """处理SSH命令执行结果"""
        try:
            print(f"[AI处理器] 处理SSH结果: {command}")
            
            # 记录命令到历史
            self.recent_commands.append(command)
            if len(self.recent_commands) > 10:
                self.recent_commands = self.recent_commands[-10:]
            
            # 检查是否有错误
            is_error = self._detect_command_error(output)
            
            if is_error:
                # 记录错误历史
                error_info = f"命令: {command} | 错误: {output[:200]}"
                self.error_history.append(error_info)
                if len(self.error_history) > 5:
                    self.error_history = self.error_history[-5:]
                
                # 生成错误恢复提示词
                error_type = self._classify_error(output)
                analysis_prompt = self.advanced_prompts.generate_error_recovery_prompt(
                    error_type, output, command
                )
            else:
                # 记录成功模式
                success_info = f"命令: {command} | 成功执行"
                self.success_patterns.append(success_info)
                if len(self.success_patterns) > 5:
                    self.success_patterns = self.success_patterns[-5:]
                
                # 使用智能分析提示词
                task_type = self.advanced_prompts.identify_task_type(command)
                complexity = ContextLevel.SIMPLE if not is_error else ContextLevel.MODERATE
                
                context = PromptContext(
                    task_type=task_type,
                    complexity=complexity,
                    user_expertise=self.user_expertise,
                    system_info=self.system_info,
                    recent_commands=self.recent_commands[-3:],
                    error_history=self.error_history[-2:],
                    success_patterns=self.success_patterns[-2:]
                )
                
                analysis_prompt = f"""SSH命令执行结果分析：

命令: {command}
输出: {output}

请分析执行结果：
1. 如果任务未完成，继续执行必要命令
2. 如果发现问题，提供解决方案
3. 如果任务完成，简要总结结果

使用SSH{{command}}格式执行后续命令。"""
            
            # 添加到对话历史
            self.conversation_history.append({
                'role': 'system',
                'content': f"SSH命令: {command}\n输出: {output[:500]}...",
                'timestamp': time.time()
            })
            
            # 发送系统消息到前端
            self.emit('system_message', {
                'message': f"命令执行完成: {command}",
                'output': output,
                'session_id': session_id
            })
            
            # 获取AI分析
            ai_analysis = self.ai_client.chat(analysis_prompt, self._get_system_prompt())
            
            print(f"[AI处理器] AI分析: {ai_analysis[:100]}...")
            
            # 添加AI分析到历史
            self.conversation_history.append({
                'role': 'assistant',
                'content': ai_analysis,
                'timestamp': time.time()
            })
            
            # 清理历史记录
            self._cleanup_history()
            
            # 解析并执行AI的后续操作
            self._parse_and_execute_ai_response(ai_analysis, session_id)
            
        except Exception as e:
            error_msg = f"处理SSH结果时发生错误: {str(e)}"
            print(f"[AI处理器] {error_msg}")
            self.emit('ai_error', {
                'error': error_msg,
                'session_id': session_id
            })
    
    def _build_ai_prompt(self, user_message: str) -> str:
        """构建智能AI提示"""
        # 识别任务类型
        task_type = self.advanced_prompts.identify_task_type(user_message)
        
        # 评估复杂度
        complexity = self.advanced_prompts.assess_complexity(user_message, self.system_info)
        
        # 构建提示词上下文
        context = PromptContext(
            task_type=task_type,
            complexity=complexity,
            user_expertise=self.user_expertise,
            system_info=self.system_info,
            recent_commands=self.recent_commands[-5:],
            error_history=self.error_history[-3:],
            success_patterns=self.success_patterns[-3:]
        )
        
        # 生成动态提示词
        return self.advanced_prompts.generate_dynamic_prompt(context, user_message)
    
    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一个智能的SSH终端助手，具备以下核心能力：

🎯 执行规则：
• 使用SSH{command}格式执行命令
• 每次执行一个命令，等待结果
• 根据输出智能决定下一步
• 自动处理常见交互场景

🧠 智能特性：
• 上下文感知和任务识别
• 错误自动恢复和替代方案
• 安全检查和风险评估
• 性能优化建议

保持高效、安全、智能。"""
    
    def _parse_and_execute_ai_response(self, ai_response: str, session_id: str):
        """解析AI响应并执行相应操作"""
        # 发送AI响应到前端
        self.emit('ai_response', {
            'response': ai_response,
            'session_id': session_id
        })
        
        # 检查是否包含SSH命令
        ssh_commands = re.findall(r'SSH\{([^}]+)\}', ai_response)
        if ssh_commands:
            for command in ssh_commands:
                print(f"[AI处理器] 执行SSH命令: {command}")
                self.ssh_executor.execute_command(command.strip(), session_id)
        
        # 检查是否需要用户输入
        input_requests = re.findall(r'INPUT\{([^}]+)\}', ai_response)
        if input_requests:
            for request in input_requests:
                self.emit('input_request', {
                    'message': request.strip(),
                    'session_id': session_id
                })
    
    def _cleanup_history(self):
        """清理对话历史，保持在限制范围内"""
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def handle_user_input(self, user_input: str, session_id: str):
        """处理用户输入（如密码、确认等）"""
        try:
            print(f"[AI处理器] 处理用户输入: {user_input}")
            
            # 发送输入到SSH执行器
            success = self.ssh_executor.send_input(user_input + '\n', session_id)
            
            if not success:
                self.emit('ai_error', {
                    'error': '发送用户输入失败',
                    'session_id': session_id
                })
            
        except Exception as e:
            error_msg = f"处理用户输入时发生错误: {str(e)}"
            print(f"[AI处理器] {error_msg}")
            self.emit('ai_error', {
                'error': error_msg,
                'session_id': session_id
            })
    
    def _detect_command_error(self, output: str) -> bool:
        """检测命令输出是否包含错误"""
        error_indicators = [
            'error:', 'Error:', 'ERROR:',
            'failed', 'Failed', 'FAILED',
            'permission denied', 'Permission denied',
            'command not found', 'Command not found',
            'no such file', 'No such file',
            'connection refused', 'Connection refused',
            'timeout', 'Timeout'
        ]
        
        output_lower = output.lower()
        return any(indicator.lower() in output_lower for indicator in error_indicators)
    
    def _classify_error(self, output: str) -> str:
        """分类错误类型"""
        output_lower = output.lower()
        
        if 'permission denied' in output_lower:
            return 'permission_error'
        elif 'command not found' in output_lower:
            return 'command_not_found'
        elif 'no such file' in output_lower:
            return 'file_not_found'
        elif 'connection' in output_lower:
            return 'connection_error'
        elif 'timeout' in output_lower:
            return 'timeout_error'
        else:
            return 'general_error'
    
    def update_system_info(self, info: Dict[str, Any]):
        """更新系统信息"""
        self.system_info.update(info)
    
    def set_user_expertise(self, level: str):
        """设置用户专业水平"""
        if level in ['beginner', 'intermediate', 'advanced']:
            self.user_expertise = level
    
    def _collect_system_info_if_needed(self):
        """在SSH连接建立时自动收集系统信息"""
        if not self.system_info_collected and self.ssh_executor:
            try:
                print("[AI处理器] 开始收集系统信息...")
                self.system_info = self.system_info_collector.collect_all_info(self.ssh_executor)
                self.system_info_collected = True
                print(f"[AI处理器] 系统信息收集完成: {list(self.system_info.keys())}")
                
                # 输出系统信息摘要
                summary = self.system_info_collector.get_system_summary()
                print(f"[AI处理器] {summary}")
                
            except Exception as e:
                print(f"[AI处理器] 收集系统信息失败: {str(e)}")
                self.system_info = {}
    
    def get_status(self) -> Dict[str, Any]:
        """获取处理器状态"""
        return {
            'conversation_length': len(self.conversation_history),
            'ssh_executor_status': self.ssh_executor.get_status() if self.ssh_executor else None,
            'recent_commands_count': len(self.recent_commands),
            'error_history_count': len(self.error_history),
            'success_patterns_count': len(self.success_patterns),
            'user_expertise': self.user_expertise,
            'system_info_collected': self.system_info_collected,
            'system_info_keys': list(self.system_info.keys()) if self.system_info else []
        }