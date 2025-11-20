from typing import Dict, List, Any, Optional
import re
import json
import time
from enum import Enum
from dataclasses import dataclass

class TaskType(Enum):
    """任务类型枚举"""
    SYSTEM_ADMIN = "system_admin"  # 系统管理
    FILE_OPERATION = "file_operation"  # 文件操作
    NETWORK_CONFIG = "network_config"  # 网络配置
    SOFTWARE_INSTALL = "software_install"  # 软件安装
    MONITORING = "monitoring"  # 系统监控
    TROUBLESHOOTING = "troubleshooting"  # 故障排除
    SECURITY = "security"  # 安全相关
    DATABASE = "database"  # 数据库操作
    WEB_SERVER = "web_server"  # Web服务器
    GENERAL = "general"  # 通用任务

class ContextLevel(Enum):
    """上下文复杂度级别"""
    SIMPLE = "simple"  # 简单任务
    MODERATE = "moderate"  # 中等复杂度
    COMPLEX = "complex"  # 复杂任务
    CRITICAL = "critical"  # 关键任务

@dataclass
class PromptContext:
    """提示词上下文"""
    task_type: TaskType
    complexity: ContextLevel
    user_expertise: str  # beginner, intermediate, expert
    system_info: Dict[str, Any]
    recent_commands: List[str]
    error_history: List[str]
    success_patterns: List[str]

class AdvancedAIPrompts:
    """高级AI提示词系统"""
    
    def __init__(self):
        self.task_patterns = self._init_task_patterns()
        self.prompt_templates = self._init_prompt_templates()
        self.context_enhancers = self._init_context_enhancers()
        self.error_recovery_prompts = self._init_error_recovery_prompts()
        
    def _init_task_patterns(self) -> Dict[TaskType, List[str]]:
        """初始化任务识别模式"""
        return {
            TaskType.SYSTEM_ADMIN: [
                r'(查看|检查|监控).*系统',
                r'(重启|关闭|启动).*服务',
                r'(用户|权限|组).*管理',
                r'系统.*状态',
                r'进程.*管理'
            ],
            TaskType.FILE_OPERATION: [
                r'(创建|删除|移动|复制).*文件',
                r'(查找|搜索).*文件',
                r'(编辑|修改).*文件',
                r'文件.*权限',
                r'目录.*操作'
            ],
            TaskType.NETWORK_CONFIG: [
                r'网络.*配置',
                r'(防火墙|iptables)',
                r'(端口|连接).*检查',
                r'(路由|网关)',
                r'(DNS|域名)'
            ],
            TaskType.SOFTWARE_INSTALL: [
                r'(安装|卸载|更新).*软件',
                r'(包|package).*管理',
                r'(依赖|dependency)',
                r'(编译|构建)',
                r'(配置|configure).*环境'
            ],
            TaskType.MONITORING: [
                r'(监控|monitor)',
                r'(性能|performance)',
                r'(日志|log).*查看',
                r'(资源|resource).*使用',
                r'(统计|statistics)'
            ],
            TaskType.TROUBLESHOOTING: [
                r'(故障|错误|问题).*排除',
                r'(调试|debug)',
                r'(修复|fix)',
                r'不.*工作',
                r'(异常|exception)'
            ],
            TaskType.SECURITY: [
                r'(安全|security)',
                r'(密码|password)',
                r'(证书|certificate)',
                r'(加密|encrypt)',
                r'(审计|audit)'
            ],
            TaskType.DATABASE: [
                r'(数据库|database)',
                r'(mysql|postgresql|mongodb)',
                r'(备份|backup).*数据',
                r'(查询|query)',
                r'(索引|index)'
            ],
            TaskType.WEB_SERVER: [
                r'(web|网站).*服务器',
                r'(nginx|apache|httpd)',
                r'(域名|domain)',
                r'(SSL|HTTPS)',
                r'(负载|load).*均衡'
            ]
        }
    
    def _init_prompt_templates(self) -> Dict[TaskType, Dict[ContextLevel, str]]:
        """初始化提示词模板"""
        return {
            TaskType.SYSTEM_ADMIN: {
                ContextLevel.SIMPLE: self._get_system_admin_simple_prompt(),
                ContextLevel.MODERATE: self._get_system_admin_moderate_prompt(),
                ContextLevel.COMPLEX: self._get_system_admin_complex_prompt(),
                ContextLevel.CRITICAL: self._get_system_admin_critical_prompt()
            },
            TaskType.FILE_OPERATION: {
                ContextLevel.SIMPLE: self._get_file_operation_simple_prompt(),
                ContextLevel.MODERATE: self._get_file_operation_moderate_prompt(),
                ContextLevel.COMPLEX: self._get_file_operation_complex_prompt(),
                ContextLevel.CRITICAL: self._get_file_operation_critical_prompt()
            },
            TaskType.SOFTWARE_INSTALL: {
                ContextLevel.SIMPLE: self._get_software_install_simple_prompt(),
                ContextLevel.MODERATE: self._get_software_install_moderate_prompt(),
                ContextLevel.COMPLEX: self._get_software_install_complex_prompt(),
                ContextLevel.CRITICAL: self._get_software_install_critical_prompt()
            },
            TaskType.TROUBLESHOOTING: {
                ContextLevel.SIMPLE: self._get_troubleshooting_simple_prompt(),
                ContextLevel.MODERATE: self._get_troubleshooting_moderate_prompt(),
                ContextLevel.COMPLEX: self._get_troubleshooting_complex_prompt(),
                ContextLevel.CRITICAL: self._get_troubleshooting_critical_prompt()
            },
            TaskType.GENERAL: {
                ContextLevel.SIMPLE: self._get_general_simple_prompt(),
                ContextLevel.MODERATE: self._get_general_moderate_prompt(),
                ContextLevel.COMPLEX: self._get_general_complex_prompt(),
                ContextLevel.CRITICAL: self._get_general_critical_prompt()
            }
        }
    
    def _init_context_enhancers(self) -> Dict[str, str]:
        """初始化上下文增强器"""
        return {
            "beginner": "\n\n🔰 新手模式：请提供详细的解释和安全提示，确保每个步骤都清晰易懂。",
            "intermediate": "\n\n⚡ 中级模式：提供高效的解决方案，适当解释关键步骤。",
            "expert": "\n\n🚀 专家模式：直接执行最优解决方案，最小化解释。",
            "error_recovery": "\n\n🔧 错误恢复模式：分析失败原因，提供替代方案，确保任务完成。",
            "safety_critical": "\n\n⚠️ 安全关键模式：执行前进行安全检查，提供回滚方案。"
        }
    
    def _init_error_recovery_prompts(self) -> Dict[str, str]:
        """初始化错误恢复提示词"""
        return {
            "command_not_found": "命令未找到，尝试查找替代命令或安装所需软件包。",
            "permission_denied": "权限不足，检查是否需要sudo权限或修改文件权限。",
            "file_not_found": "文件不存在，检查路径是否正确或创建所需文件。",
            "network_error": "网络错误，检查网络连接和防火墙设置。",
            "service_failed": "服务启动失败，检查配置文件和依赖服务。",
            "disk_full": "磁盘空间不足，清理临时文件或扩展存储空间。",
            "syntax_error": "语法错误，检查命令格式和参数。"
        }
    
    def identify_task_type(self, user_message: str) -> TaskType:
        """识别任务类型"""
        message_lower = user_message.lower()
        
        for task_type, patterns in self.task_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return task_type
        
        return TaskType.GENERAL
    
    def assess_complexity(self, user_message: str, context: Dict[str, Any]) -> ContextLevel:
        """评估任务复杂度"""
        complexity_indicators = {
            ContextLevel.CRITICAL: [
                '生产环境', '关键系统', '数据库', '备份', '恢复',
                '安全', '防火墙', '权限', '密码', '证书'
            ],
            ContextLevel.COMPLEX: [
                '配置', '编译', '构建', '部署', '集群',
                '负载均衡', '监控', '日志分析', '性能优化'
            ],
            ContextLevel.MODERATE: [
                '安装', '更新', '启动', '停止', '重启',
                '查看', '检查', '修改', '创建'
            ]
        }
        
        message_lower = user_message.lower()
        
        for level, indicators in complexity_indicators.items():
            if any(indicator in message_lower for indicator in indicators):
                return level
        
        return ContextLevel.SIMPLE
    
    def generate_dynamic_prompt(self, context: PromptContext, user_message: str) -> str:
        """生成动态提示词"""
        # 获取基础模板
        base_template = self.prompt_templates.get(
            context.task_type, 
            self.prompt_templates[TaskType.GENERAL]
        ).get(context.complexity, self._get_general_simple_prompt())
        
        # 添加上下文增强
        expertise_enhancer = self.context_enhancers.get(context.user_expertise, "")
        
        # 添加历史上下文
        history_context = self._build_history_context(context)
        
        # 添加系统信息（增强版）
        system_context = self._build_enhanced_system_context(context.system_info)
        
        # 添加任务特定的上下文提示
        task_specific_context = self._build_task_specific_context(context.task_type, context.system_info)
        
        # 组合最终提示词
        final_prompt = f"""{base_template}

{system_context}

{task_specific_context}

{history_context}

{expertise_enhancer}

当前任务: {user_message}"""
        
        return final_prompt.strip()
    
    def _build_history_context(self, context: PromptContext) -> str:
        """构建历史上下文"""
        history_parts = []
        
        if context.recent_commands:
            recent_cmds = '\n'.join(context.recent_commands[-3:])
            history_parts.append(f"📋 最近执行的命令:\n{recent_cmds}")
        
        if context.error_history:
            recent_errors = '\n'.join(context.error_history[-2:])
            history_parts.append(f"❌ 最近的错误:\n{recent_errors}")
        
        if context.success_patterns:
            recent_success = '\n'.join(context.success_patterns[-2:])
            history_parts.append(f"✅ 成功模式:\n{recent_success}")
        
        return '\n\n'.join(history_parts) if history_parts else ""
    
    def _build_system_context(self, system_info: Dict[str, Any]) -> str:
        """构建系统上下文"""
        if not system_info:
            return ""
        
        context_parts = []
        
        if 'os' in system_info:
            context_parts.append(f"🖥️ 操作系统: {system_info['os']}")
        
        if 'arch' in system_info:
            context_parts.append(f"🏗️ 架构: {system_info['arch']}")
        
        if 'user' in system_info:
            context_parts.append(f"👤 当前用户: {system_info['user']}")
        
        if 'pwd' in system_info:
            context_parts.append(f"📁 当前目录: {system_info['pwd']}")
        
        return '\n'.join(context_parts) if context_parts else ""
    
    def _build_enhanced_system_context(self, system_info: Dict[str, Any]) -> str:
        """构建增强的系统上下文"""
        if not system_info:
            return ""
        
        context_parts = []
        
        # 基础系统信息
        if 'os' in system_info:
            context_parts.append(f"🖥️ 操作系统: {system_info['os']}")
        
        if 'arch' in system_info:
            context_parts.append(f"🏗️ 架构: {system_info['arch']}")
        
        if 'user' in system_info:
            context_parts.append(f"👤 当前用户: {system_info['user']}")
        
        if 'pwd' in system_info:
            context_parts.append(f"📁 当前目录: {system_info['pwd']}")
        
        # 系统资源信息
        if 'memory' in system_info:
            context_parts.append(f"💾 内存使用: {system_info['memory']}")
        
        if 'disk' in system_info:
            context_parts.append(f"💿 磁盘使用: {system_info['disk']}")
        
        if 'cpu' in system_info:
            context_parts.append(f"⚡ CPU负载: {system_info['cpu']}")
        
        # 网络信息
        if 'network' in system_info:
            context_parts.append(f"🌐 网络状态: {system_info['network']}")
        
        # 运行的服务
        if 'services' in system_info:
            context_parts.append(f"🔧 关键服务: {system_info['services']}")
        
        return '\n'.join(context_parts) if context_parts else ""
    
    def _build_task_specific_context(self, task_type: TaskType, system_info: Dict[str, Any]) -> str:
        """构建任务特定的上下文提示"""
        if not system_info:
            return ""
        
        context_parts = []
        
        if task_type == TaskType.SYSTEM_ADMIN:
            if 'services' in system_info:
                context_parts.append(f"🔧 系统服务状态已收集，可进行服务管理操作")
            if 'memory' in system_info:
                context_parts.append(f"💾 内存状态已监控，可进行资源优化")
        
        elif task_type == TaskType.FILE_OPERATION:
            if 'disk' in system_info:
                context_parts.append(f"💿 磁盘空间已检查，可安全进行文件操作")
            if 'pwd' in system_info:
                context_parts.append(f"📁 当前工作目录已确认")
        
        elif task_type == TaskType.NETWORK_CONFIG:
            if 'network' in system_info:
                context_parts.append(f"🌐 网络配置信息已获取，可进行网络诊断")
        
        elif task_type == TaskType.SOFTWARE_INSTALL:
            if 'os' in system_info:
                context_parts.append(f"🖥️ 系统版本已确认，可选择合适的软件包")
            if 'disk' in system_info:
                context_parts.append(f"💿 存储空间已检查，可进行软件安装")
        
        elif task_type == TaskType.MONITORING:
            if 'cpu' in system_info or 'memory' in system_info:
                context_parts.append(f"📊 系统性能数据已收集，可进行深度分析")
        
        return '\n'.join(context_parts) if context_parts else ""
    
    def generate_error_recovery_prompt(self, error_type: str, error_output: str, original_command: str) -> str:
        """生成错误恢复提示词"""
        base_recovery = self.error_recovery_prompts.get(error_type, "分析错误并提供解决方案。")
        
        return f"""🔧 错误恢复模式激活

原始命令: {original_command}
错误输出: {error_output}

{base_recovery}

请分析错误原因并执行以下步骤：
1. 诊断具体问题
2. 提供解决方案
3. 执行修复命令
4. 验证修复结果

使用SSH{{command}}格式执行命令。保持简洁高效。"""
    
    # 以下是各种提示词模板的实现
    def _get_system_admin_simple_prompt(self) -> str:
        return """🔧 系统管理助手 - 简单模式

你是一个专业的Linux系统管理员，专注于执行系统管理任务。

核心原则：
• 直接执行命令，使用SSH{command}格式
• 每次执行一个命令，等待结果
• 提供简洁的状态反馈
• 确保操作安全性

执行策略：
1. 先检查当前状态
2. 执行必要操作
3. 验证结果
4. 报告完成状态"""
    
    def _get_system_admin_moderate_prompt(self) -> str:
        return """🔧 系统管理助手 - 中级模式

你是一个经验丰富的系统管理员，能够处理复杂的系统管理任务。

核心能力：
• 系统状态监控和诊断
• 服务管理和配置
• 用户和权限管理
• 性能优化建议

执行流程：
1. 分析系统环境
2. 制定执行计划
3. 逐步执行命令
4. 监控执行结果
5. 提供优化建议

使用SSH{command}格式执行所有命令。"""
    
    def _get_system_admin_complex_prompt(self) -> str:
        return """🔧 系统管理助手 - 复杂模式

你是一个高级系统架构师，能够处理复杂的企业级系统管理任务。

专业领域：
• 高可用性系统配置
• 集群管理和负载均衡
• 安全加固和合规性
• 自动化运维脚本
• 故障排除和性能调优

执行方法：
1. 全面系统分析
2. 风险评估和预案
3. 分阶段执行
4. 实时监控和调整
5. 文档化和总结

每个命令都要考虑系统稳定性和安全性。"""
    
    def _get_system_admin_critical_prompt(self) -> str:
        return """🔧 系统管理助手 - 关键模式

⚠️ 关键系统操作模式 - 最高安全级别

你正在处理生产环境的关键系统，必须遵循最严格的安全协议。

安全原则：
• 每个操作前进行安全检查
• 创建备份和回滚点
• 最小化系统影响
• 详细记录所有操作
• 验证每个步骤的结果

执行协议：
1. 🔍 系统状态评估
2. 💾 创建备份点
3. 🧪 测试环境验证
4. ⚡ 最小化影响执行
5. ✅ 全面结果验证
6. 📝 操作记录归档

绝不执行可能导致系统不稳定的操作。"""
    
    def _get_file_operation_simple_prompt(self) -> str:
        return """📁 文件操作助手 - 简单模式

专注于基础文件和目录操作。

核心功能：
• 文件创建、删除、移动、复制
• 目录浏览和管理
• 权限查看和修改
• 文件内容查看和编辑

操作流程：
1. 确认目标路径
2. 检查权限和空间
3. 执行文件操作
4. 验证操作结果

使用SSH{command}格式执行命令。"""
    
    def _get_file_operation_moderate_prompt(self) -> str:
        return """📁 文件操作助手 - 中级模式

处理复杂的文件系统操作和批量处理。

高级功能：
• 批量文件操作
• 文件搜索和过滤
• 压缩和解压缩
• 文件同步和备份
• 符号链接管理

执行策略：
1. 分析文件结构
2. 优化操作顺序
3. 批量处理执行
4. 进度监控
5. 结果验证"""
    
    def _get_file_operation_complex_prompt(self) -> str:
        return """📁 文件操作助手 - 复杂模式

处理企业级文件系统管理和自动化操作。

专业能力：
• 大规模文件迁移
• 文件系统性能优化
• 自动化备份策略
• 文件完整性检查
• 存储空间管理

执行方案：
1. 文件系统分析
2. 性能影响评估
3. 分批次执行
4. 实时监控
5. 完整性验证"""
    
    def _get_file_operation_critical_prompt(self) -> str:
        return """📁 文件操作助手 - 关键模式

⚠️ 关键数据操作 - 最高安全级别

处理重要数据文件，必须确保数据安全。

安全协议：
• 操作前创建完整备份
• 验证数据完整性
• 最小化数据丢失风险
• 详细操作日志

执行流程：
1. 💾 数据备份
2. 🔍 完整性检查
3. 🧪 小范围测试
4. ⚡ 谨慎执行
5. ✅ 数据验证
6. 📝 操作记录"""
    
    def _get_software_install_simple_prompt(self) -> str:
        return """📦 软件安装助手 - 简单模式

专注于基础软件包管理。

核心功能：
• 软件包安装和卸载
• 依赖关系处理
• 软件包搜索
• 版本管理

安装流程：
1. 检查系统兼容性
2. 更新包管理器
3. 安装软件包
4. 验证安装结果

使用SSH{command}格式执行命令。"""
    
    def _get_software_install_moderate_prompt(self) -> str:
        return """📦 软件安装助手 - 中级模式

处理复杂的软件部署和配置。

高级功能：
• 源码编译安装
• 多版本软件管理
• 环境配置和优化
• 服务配置和启动

部署策略：
1. 环境准备和检查
2. 依赖关系解析
3. 编译和安装
4. 配置和测试
5. 服务启动和验证"""
    
    def _get_software_install_complex_prompt(self) -> str:
        return """📦 软件安装助手 - 复杂模式

处理企业级软件部署和集群配置。

专业能力：
• 分布式软件部署
• 容器化部署
• 自动化配置管理
• 性能调优
• 监控和日志配置

部署方案：
1. 架构设计和规划
2. 环境标准化
3. 自动化部署
4. 集群配置
5. 监控和维护"""
    
    def _get_software_install_critical_prompt(self) -> str:
        return """📦 软件安装助手 - 关键模式

⚠️ 生产环境部署 - 最高安全级别

在生产环境中部署关键软件系统。

安全原则：
• 零停机部署策略
• 完整回滚方案
• 安全漏洞检查
• 性能影响评估

部署协议：
1. 🔍 环境评估
2. 💾 系统备份
3. 🧪 测试环境验证
4. ⚡ 蓝绿部署
5. ✅ 健康检查
6. 📝 部署文档"""
    
    def _get_troubleshooting_simple_prompt(self) -> str:
        return """🔍 故障排除助手 - 简单模式

专注于基础问题诊断和解决。

诊断能力：
• 系统状态检查
• 日志分析
• 服务状态诊断
• 基础性能检查

排除流程：
1. 问题现象确认
2. 基础状态检查
3. 日志错误分析
4. 解决方案执行
5. 问题解决验证

使用SSH{command}格式执行诊断命令。"""
    
    def _get_troubleshooting_moderate_prompt(self) -> str:
        return """🔍 故障排除助手 - 中级模式

处理复杂的系统故障和性能问题。

高级诊断：
• 深度日志分析
• 性能瓶颈识别
• 网络连接诊断
• 资源使用分析
• 配置问题排查

排除策略：
1. 多维度问题分析
2. 系统性能评估
3. 根因分析
4. 分步骤解决
5. 预防措施建议"""
    
    def _get_troubleshooting_complex_prompt(self) -> str:
        return """🔍 故障排除助手 - 复杂模式

处理企业级系统故障和架构问题。

专家级诊断：
• 分布式系统故障分析
• 集群健康状态诊断
• 性能调优和优化
• 安全事件调查
• 容量规划分析

解决方案：
1. 全栈问题分析
2. 影响范围评估
3. 紧急修复措施
4. 长期解决方案
5. 系统改进建议"""
    
    def _get_troubleshooting_critical_prompt(self) -> str:
        return """🔍 故障排除助手 - 关键模式

⚠️ 生产环境紧急故障处理

处理影响业务的关键系统故障。

紧急响应：
• 快速影响评估
• 紧急止损措施
• 根因快速定位
• 最小化业务影响

应急流程：
1. 🚨 故障确认和分级
2. 🛡️ 紧急止损
3. 🔍 快速诊断
4. ⚡ 临时修复
5. ✅ 服务恢复验证
6. 📋 事后分析报告"""
    
    def _get_general_simple_prompt(self) -> str:
        return """🤖 智能SSH助手 - 简单模式

我是你的Linux终端智能助手，专注于高效执行任务。

核心能力：
• 直接执行SSH命令
• 智能分析结果
• 提供简洁反馈
• 自动处理常见问题

工作方式：
1. 理解你的需求
2. 执行必要命令
3. 分析执行结果
4. 提供状态反馈

使用SSH{command}格式执行所有命令。保持简洁高效。"""
    
    def _get_general_moderate_prompt(self) -> str:
        return """🤖 智能SSH助手 - 中级模式

我是你的高级Linux系统助手，能够处理复杂的系统管理任务。

增强能力：
• 多步骤任务规划
• 智能错误恢复
• 性能优化建议
• 安全最佳实践

执行策略：
1. 任务分析和规划
2. 分步骤执行
3. 实时监控和调整
4. 结果验证和优化
5. 经验总结和建议

每个操作都考虑系统稳定性和安全性。"""
    
    def _get_general_complex_prompt(self) -> str:
        return """🤖 智能SSH助手 - 复杂模式

我是你的专家级系统架构师，能够处理企业级复杂任务。

专家能力：
• 系统架构设计
• 自动化解决方案
• 性能调优和监控
• 安全加固和合规
• 故障预防和恢复

工作方法：
1. 深度需求分析
2. 架构设计和规划
3. 分阶段实施
4. 持续监控和优化
5. 文档化和知识传递

每个决策都基于最佳实践和行业标准。"""
    
    def _get_general_critical_prompt(self) -> str:
        return """🤖 智能SSH助手 - 关键模式

⚠️ 生产环境操作 - 最高安全级别

我是你的首席系统工程师，专门处理关键生产环境任务。

关键原则：
• 零风险操作策略
• 完整的备份和回滚
• 最小化业务影响
• 详细的操作审计
• 实时监控和告警

执行标准：
1. 🔒 安全评估和授权
2. 💾 完整备份策略
3. 🧪 测试环境验证
4. ⚡ 谨慎生产执行
5. 📊 实时监控
6. 📝 完整操作记录

绝不执行任何可能影响生产稳定性的操作。"""