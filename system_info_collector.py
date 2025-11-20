from typing import Dict, Any, Optional
import re
import json

class SystemInfoCollector:
    """系统信息收集器 - 自动收集SSH连接的系统信息"""
    
    def __init__(self, ssh_executor=None):
        self.ssh_executor = ssh_executor
        self.system_info = {}
        self.collection_commands = {
            'os': 'uname -a',
            'distribution': 'cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || echo "Unknown"',
            'architecture': 'uname -m',
            'kernel': 'uname -r',
            'hostname': 'hostname',
            'user': 'whoami',
            'home': 'echo $HOME',
            'shell': 'echo $SHELL',
            'pwd': 'pwd',
            'cpu_info': 'cat /proc/cpuinfo | grep "model name" | head -1 | cut -d":" -f2 | xargs',
            'memory': 'free -h | grep Mem | awk "{print $2}"',
            'disk_usage': 'df -h / | tail -1 | awk "{print $2, $3, $4, $5}"',
            'uptime': 'uptime | awk "{print $3, $4}" | sed "s/,//"',
            'load_average': 'uptime | awk -F"load average:" "{print $2}"',
            'processes': 'ps aux | wc -l',
            'network_interfaces': 'ip addr show | grep "inet " | grep -v "127.0.0.1" | awk "{print $2}" | head -3',
            'package_manager': 'which apt-get yum dnf pacman zypper 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo "unknown"',
            'python_version': 'python3 --version 2>/dev/null || python --version 2>/dev/null || echo "Not installed"',
            'docker_status': 'docker --version 2>/dev/null || echo "Not installed"',
            'git_version': 'git --version 2>/dev/null || echo "Not installed"',
            'timezone': 'timedatectl show --property=Timezone --value 2>/dev/null || date +%Z'
        }
    
    async def collect_system_info(self, session_id: str) -> Dict[str, Any]:
        """收集完整的系统信息"""
        print("[系统信息收集器] 开始收集系统信息...")
        
        collected_info = {}
        
        for info_type, command in self.collection_commands.items():
            try:
                # 执行命令获取信息
                output = await self._execute_info_command(command, session_id)
                if output and output.strip():
                    collected_info[info_type] = self._clean_output(output)
                    print(f"[系统信息收集器] 收集 {info_type}: {collected_info[info_type][:50]}...")
            except Exception as e:
                print(f"[系统信息收集器] 收集 {info_type} 失败: {e}")
                collected_info[info_type] = "Unknown"
        
        # 解析和增强信息
        enhanced_info = self._enhance_system_info(collected_info)
        
        self.system_info = enhanced_info
        print(f"[系统信息收集器] 系统信息收集完成，共收集 {len(enhanced_info)} 项信息")
        
        return enhanced_info
    
    def collect_all_info(self, ssh_executor) -> Dict[str, Any]:
        """同步收集系统信息（用于SSH连接建立时）"""
        self.ssh_executor = ssh_executor
        print("[系统信息收集器] 开始同步收集系统信息...")
        
        collected_info = {}
        
        # 基础信息收集命令（优先级高，快速执行）
        priority_commands = {
            'os': 'uname -a',
            'user': 'whoami',
            'pwd': 'pwd',
            'hostname': 'hostname',
            'shell': 'echo $SHELL',
            'home': 'echo $HOME'
        }
        
        # 先收集基础信息
        for info_type, command in priority_commands.items():
            try:
                output = self._execute_sync_command(command)
                if output and output.strip():
                    collected_info[info_type] = self._clean_output(output)
                    print(f"[系统信息收集器] 收集 {info_type}: {collected_info[info_type]}")
            except Exception as e:
                print(f"[系统信息收集器] 收集 {info_type} 失败: {e}")
                collected_info[info_type] = "Unknown"
        
        # 收集扩展信息（可能较慢）
        extended_commands = {
            'distribution': 'cat /etc/os-release 2>/dev/null | head -5 || echo "Unknown"',
            'architecture': 'uname -m',
            'kernel': 'uname -r',
            'package_manager': 'which apt-get yum dnf pacman 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo "unknown"',
            'python_version': 'python3 --version 2>/dev/null || python --version 2>/dev/null || echo "Not installed"',
            'memory': 'free -h 2>/dev/null | grep Mem | awk "{print $2}" || echo "Unknown"'
        }
        
        for info_type, command in extended_commands.items():
            try:
                output = self._execute_sync_command(command)
                if output and output.strip():
                    collected_info[info_type] = self._clean_output(output)
            except Exception as e:
                print(f"[系统信息收集器] 收集 {info_type} 失败: {e}")
                collected_info[info_type] = "Unknown"
        
        # 解析和增强信息
        enhanced_info = self._enhance_system_info(collected_info)
        self.system_info = enhanced_info
        
        print(f"[系统信息收集器] 同步收集完成，共收集 {len(enhanced_info)} 项信息")
        return enhanced_info
    
    def _execute_sync_command(self, command: str) -> str:
        """同步执行信息收集命令"""
        if not self.ssh_executor:
            return ""
        
        try:
            # 使用SSH执行器执行命令
            result = self.ssh_executor.execute_command(command)
            if result and 'output' in result:
                return result['output']
            return ""
        except Exception as e:
            print(f"[系统信息收集器] 执行命令失败 '{command}': {e}")
            return ""
    
    async def _execute_info_command(self, command: str, session_id: str) -> str:
        """执行信息收集命令"""
        # 这里需要与SSH执行器集成
        # 暂时返回模拟数据，实际实现时需要调用SSH执行器
        return ""
    
    def _clean_output(self, output: str) -> str:
        """清理命令输出"""
        # 移除ANSI转义序列
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', output)
        
        # 移除多余的空白字符
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
    
    def _enhance_system_info(self, raw_info: Dict[str, str]) -> Dict[str, Any]:
        """增强和解析系统信息"""
        enhanced = {}
        
        # 操作系统信息
        if 'os' in raw_info:
            os_info = raw_info['os']
            enhanced['os'] = {
                'full': os_info,
                'type': self._detect_os_type(os_info),
                'is_linux': 'Linux' in os_info,
                'is_unix': any(x in os_info.lower() for x in ['linux', 'unix', 'darwin', 'bsd'])
            }
        
        # 发行版信息
        if 'distribution' in raw_info:
            enhanced['distribution'] = self._parse_distribution(raw_info['distribution'])
        
        # 硬件信息
        enhanced['hardware'] = {
            'architecture': raw_info.get('architecture', 'Unknown'),
            'cpu': raw_info.get('cpu_info', 'Unknown'),
            'memory': raw_info.get('memory', 'Unknown')
        }
        
        # 系统状态
        enhanced['system_status'] = {
            'uptime': raw_info.get('uptime', 'Unknown'),
            'load_average': raw_info.get('load_average', 'Unknown'),
            'processes': raw_info.get('processes', 'Unknown'),
            'disk_usage': self._parse_disk_usage(raw_info.get('disk_usage', ''))
        }
        
        # 用户环境
        enhanced['user_environment'] = {
            'user': raw_info.get('user', 'Unknown'),
            'home': raw_info.get('home', 'Unknown'),
            'shell': raw_info.get('shell', 'Unknown'),
            'pwd': raw_info.get('pwd', 'Unknown'),
            'timezone': raw_info.get('timezone', 'Unknown')
        }
        
        # 网络信息
        if 'network_interfaces' in raw_info:
            enhanced['network'] = {
                'interfaces': raw_info['network_interfaces'].split('\n') if raw_info['network_interfaces'] else [],
                'hostname': raw_info.get('hostname', 'Unknown')
            }
        
        # 软件环境
        enhanced['software'] = {
            'package_manager': raw_info.get('package_manager', 'Unknown'),
            'python': raw_info.get('python_version', 'Not installed'),
            'docker': raw_info.get('docker_status', 'Not installed'),
            'git': raw_info.get('git_version', 'Not installed'),
            'kernel': raw_info.get('kernel', 'Unknown')
        }
        
        # 系统能力评估
        enhanced['capabilities'] = self._assess_system_capabilities(enhanced)
        
        return enhanced
    
    def _detect_os_type(self, os_info: str) -> str:
        """检测操作系统类型"""
        os_lower = os_info.lower()
        
        if 'ubuntu' in os_lower:
            return 'Ubuntu'
        elif 'centos' in os_lower:
            return 'CentOS'
        elif 'redhat' in os_lower or 'rhel' in os_lower:
            return 'RedHat'
        elif 'debian' in os_lower:
            return 'Debian'
        elif 'fedora' in os_lower:
            return 'Fedora'
        elif 'suse' in os_lower:
            return 'SUSE'
        elif 'arch' in os_lower:
            return 'Arch'
        elif 'alpine' in os_lower:
            return 'Alpine'
        elif 'darwin' in os_lower:
            return 'macOS'
        elif 'linux' in os_lower:
            return 'Linux'
        else:
            return 'Unknown'
    
    def _parse_distribution(self, dist_info: str) -> Dict[str, str]:
        """解析发行版信息"""
        result = {'name': 'Unknown', 'version': 'Unknown', 'id': 'Unknown'}
        
        # 解析 /etc/os-release 格式
        for line in dist_info.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"')
                
                if key == 'NAME':
                    result['name'] = value
                elif key == 'VERSION':
                    result['version'] = value
                elif key == 'ID':
                    result['id'] = value
        
        return result
    
    def _parse_disk_usage(self, disk_info: str) -> Dict[str, str]:
        """解析磁盘使用信息"""
        if not disk_info or len(disk_info.split()) < 4:
            return {'total': 'Unknown', 'used': 'Unknown', 'available': 'Unknown', 'usage_percent': 'Unknown'}
        
        parts = disk_info.split()
        return {
            'total': parts[0],
            'used': parts[1],
            'available': parts[2],
            'usage_percent': parts[3]
        }
    
    def _assess_system_capabilities(self, system_info: Dict[str, Any]) -> Dict[str, bool]:
        """评估系统能力"""
        capabilities = {
            'has_package_manager': system_info.get('software', {}).get('package_manager', 'unknown') != 'unknown',
            'has_python': 'Not installed' not in system_info.get('software', {}).get('python', ''),
            'has_docker': 'Not installed' not in system_info.get('software', {}).get('docker', ''),
            'has_git': 'Not installed' not in system_info.get('software', {}).get('git', ''),
            'is_root': system_info.get('user_environment', {}).get('user', '') == 'root',
            'is_linux': system_info.get('os', {}).get('is_linux', False),
            'has_systemd': False,  # 需要额外检测
            'has_network': len(system_info.get('network', {}).get('interfaces', [])) > 0
        }
        
        return capabilities
    
    def get_system_summary(self) -> str:
        """获取系统信息摘要"""
        if not self.system_info:
            return "系统信息未收集"
        
        os_info = self.system_info.get('os', {})
        dist_info = self.system_info.get('distribution', {})
        hardware = self.system_info.get('hardware', {})
        user_env = self.system_info.get('user_environment', {})
        
        summary = f"""系统概览：
🖥️ 操作系统: {dist_info.get('name', 'Unknown')} {dist_info.get('version', '')}
🏗️ 架构: {hardware.get('architecture', 'Unknown')}
👤 用户: {user_env.get('user', 'Unknown')}
📁 当前目录: {user_env.get('pwd', 'Unknown')}
💾 内存: {hardware.get('memory', 'Unknown')}
🔧 包管理器: {self.system_info.get('software', {}).get('package_manager', 'Unknown')}"""
        
        return summary
    
    def get_context_for_task(self, task_type: str) -> Dict[str, Any]:
        """根据任务类型获取相关的上下文信息"""
        if not self.system_info:
            return {}
        
        context = {
            'os_type': self.system_info.get('os', {}).get('type', 'Unknown'),
            'package_manager': self.system_info.get('software', {}).get('package_manager', 'unknown'),
            'user': self.system_info.get('user_environment', {}).get('user', 'unknown'),
            'capabilities': self.system_info.get('capabilities', {})
        }
        
        # 根据任务类型添加特定信息
        if task_type in ['software_install', 'package_management']:
            context['python_available'] = self.system_info.get('capabilities', {}).get('has_python', False)
            context['docker_available'] = self.system_info.get('capabilities', {}).get('has_docker', False)
            context['git_available'] = self.system_info.get('capabilities', {}).get('has_git', False)
        
        elif task_type in ['system_admin', 'monitoring']:
            context['system_status'] = self.system_info.get('system_status', {})
            context['is_root'] = self.system_info.get('capabilities', {}).get('is_root', False)
        
        elif task_type in ['network_config', 'security']:
            context['network'] = self.system_info.get('network', {})
            context['hostname'] = self.system_info.get('network', {}).get('hostname', 'unknown')
        
        return context
    
    def update_dynamic_info(self, info_type: str, value: str):
        """更新动态信息（如当前目录）"""
        if info_type == 'pwd':
            if 'user_environment' not in self.system_info:
                self.system_info['user_environment'] = {}
            self.system_info['user_environment']['pwd'] = value
        
        elif info_type == 'user':
            if 'user_environment' not in self.system_info:
                self.system_info['user_environment'] = {}
            self.system_info['user_environment']['user'] = value
            
            # 更新能力评估
            if 'capabilities' not in self.system_info:
                self.system_info['capabilities'] = {}
            self.system_info['capabilities']['is_root'] = (value == 'root')
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取完整的系统信息"""
        return self.system_info.copy()
    
    def is_info_collected(self) -> bool:
        """检查系统信息是否已收集"""
        return bool(self.system_info)