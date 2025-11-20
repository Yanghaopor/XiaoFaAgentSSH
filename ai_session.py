from typing import List, Dict, Any
import time

class AISession:
    """
    AI会话管理器，维护统一的对话上下文
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Dict[str, str]] = []
        self.created_at = time.time()
        self.last_activity = time.time()
        
        # 初始化系统消息
        self.add_system_message(
            "你是一个专业的SSH终端助手，具备自主执行能力。你可以：\n"
            "1. 分析SSH命令的执行结果\n"
            "2. 回答用户的技术问题\n"
            "3. 提供系统管理建议\n"
            "4. 自主执行SSH命令来帮助用户\n\n"
            "**重要：你具备代理执行能力，可以使用以下格式：**\n"
            "- SSH{命令}: 自动执行SSH命令，如 SSH{ls -la /}\n"
            "- EC{\"按键1\",\"按键2\"}: 发送快捷键，如 EC{\"ctrl\",\"c\"}\n"
            "- WAIT{秒数}: 等待指定时间，如 WAIT{3}\n\n"
            "当用户需要查看文件、目录或执行命令时，你可以直接使用SSH{命令}格式来执行，\n"
            "而不是让用户手动输入。这样可以提供更好的用户体验。\n\n"
            "请根据上下文提供准确、简洁的回答，并在适当时候主动执行命令。"
        )
    
    def add_system_message(self, content: str):
        """添加系统消息"""
        self.messages.append({
            "role": "system",
            "content": content
        })
        self.last_activity = time.time()
    
    def add_ssh_output(self, command: str, output: str):
        """添加SSH命令输出到上下文"""
        content = f"[SSH命令执行]\n命令: {command}\n输出: {output}"
        self.messages.append({
            "role": "system",
            "content": content
        })
        self.last_activity = time.time()
    
    def add_user_message(self, content: str):
        """添加用户消息"""
        self.messages.append({
            "role": "user",
            "content": content
        })
        self.last_activity = time.time()
    
    def add_assistant_message(self, content: str):
        """添加AI回复消息"""
        self.messages.append({
            "role": "assistant",
            "content": content
        })
        self.last_activity = time.time()
    
    def get_messages(self) -> List[Dict[str, str]]:
        """获取所有消息"""
        return self.messages.copy()
    
    def get_recent_messages(self, limit: int = 20) -> List[Dict[str, str]]:
        """获取最近的消息（限制数量以控制token使用）"""
        if len(self.messages) <= limit:
            return self.messages.copy()
        
        # 保留系统消息和最近的对话
        system_messages = [msg for msg in self.messages if msg["role"] == "system"]
        recent_messages = self.messages[-limit:]
        
        # 如果最近消息中没有系统消息，添加最新的系统消息
        if not any(msg["role"] == "system" for msg in recent_messages):
            if system_messages:
                return [system_messages[-1]] + recent_messages
        
        return recent_messages
    
    def is_expired(self, timeout: int = 3600) -> bool:
        """检查会话是否过期（默认1小时）"""
        return time.time() - self.last_activity > timeout
    
    def clear_old_messages(self, keep_count: int = 50):
        """清理旧消息，保留最近的消息"""
        if len(self.messages) > keep_count:
            # 保留系统消息和最近的对话
            system_messages = [msg for msg in self.messages if msg["role"] == "system"]
            recent_messages = self.messages[-keep_count:]
            
            # 合并系统消息和最近消息
            self.messages = system_messages + recent_messages
            # 去重
            seen = set()
            unique_messages = []
            for msg in self.messages:
                msg_key = (msg["role"], msg["content"])
                if msg_key not in seen:
                    seen.add(msg_key)
                    unique_messages.append(msg)
            self.messages = unique_messages


class AISessionManager:
    """
    AI会话管理器，管理多个用户的会话
    """
    
    def __init__(self):
        self.sessions: Dict[str, AISession] = {}
    
    def get_session(self, session_id: str) -> AISession:
        """获取或创建会话"""
        if session_id not in self.sessions:
            self.sessions[session_id] = AISession(session_id)
        else:
            # 清理过期会话
            self.cleanup_expired_sessions()
        
        return self.sessions[session_id]
    
    def cleanup_expired_sessions(self, timeout: int = 3600):
        """清理过期会话"""
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired(timeout)
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
    
    def get_session_count(self) -> int:
        """获取活跃会话数量"""
        return len(self.sessions)
