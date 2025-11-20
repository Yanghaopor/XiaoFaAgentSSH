import os
import json
import base64
import requests
import dashscope
from openai import OpenAI
from typing import List, Dict, Any, Optional

class QwenClient:
    """
    阿里千问API客户端封装类
    用于简化千问模型的调用
    """
    
    def __init__(self, config_path: str = 'User/User.json'):
        """
        初始化千问客户端
        
        Args:
            config_path: 配置文件的路径
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.api_key = config.get("api_key") or os.getenv("DASHSCOPE_API_KEY")
        self.base_url = config.get("base_url")
        self.models = {model['type']: model['model_name'] for model in config.get("models", [])}
        
        if not self.api_key:
            raise ValueError("API密钥未在配置文件或环境变量中设置")
            
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except Exception as e:
            # 如果OpenAI客户端初始化失败，尝试使用更简单的方式
            print(f"OpenAI客户端初始化失败: {e}")
            self.client = None
    
    def get_model(self, model_type: str) -> str:
        """
        根据类型获取模型名称
        
        Args:
            model_type: 模型类型 (e.g., 'general', 'vision', 'code')
            
        Returns:
            模型名称
        """
        model = self.models.get(model_type)
        if not model:
            raise ValueError(f"未找到类型为 '{model_type}' 的模型配置")
        return model

    def chat_completion(self, 
                       messages: List[Dict[str, Any]], 
                       model: str,
                       enable_thinking: Optional[bool] = None,
                       **kwargs) -> Any:
        """
        创建聊天完成
        
        Args:
            messages: 消息列表
            model: 使用的模型名称
            enable_thinking: 是否启用思考过程（仅Qwen3模型支持）
            **kwargs: 其他参数
            
        Returns:
            API响应结果
        """
        params = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        if enable_thinking is not None:
            params["extra_body"] = {"enable_thinking": enable_thinking}
            
        return self.client.chat.completions.create(**params)
    
    def chat(self, user_message: str, system_message: str = "You are a helpful assistant.", model_type: str = "general") -> str:
        """
        简单聊天接口
        
        Args:
            user_message: 用户消息
            system_message: 系统消息
            model_type: 模型类型
            
        Returns:
            AI回复内容
        """
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        return self.chat_with_messages(messages, model_type)
    
    def chat_with_messages(self, messages: list, model_type: str = "general") -> str:
        """
        使用消息列表进行聊天
        
        Args:
            messages: 消息列表，格式为 [{"role": "system/user/assistant", "content": "消息内容"}]
            model_type: 模型类型
            
        Returns:
            AI回复内容
        """
        if not self.client:
            # 使用requests直接调用API作为备用方案
            return self._chat_with_messages_requests(messages, model_type)
            
        try:
            model = self.get_model(model_type)
            response = self.chat_completion(messages, model)
            return response.choices[0].message.content
        except Exception as e:
            # 如果OpenAI客户端失败，尝试requests备用方案
            return self._chat_with_messages_requests(messages, model_type)
    
    def _chat_with_requests(self, user_message: str, system_message: str = "You are a helpful assistant.", model_type: str = "general") -> str:
        """
        使用requests直接调用千问API的备用方案
        """
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        return self._chat_with_messages_requests(messages, model_type)
    
    def _chat_with_messages_requests(self, messages: list, model_type: str = "general") -> str:
        """
        使用requests直接调用千问API的备用方案（支持消息列表）
        """
        try:
            model = self.get_model(model_type)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": messages
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return f"API调用失败: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"AI回复失败: {e}"
    
    def simple_chat(self, user_message: str, system_message: str = "You are a helpful assistant.", model_type: str = "general") -> str:
        """
        简单的聊天接口（别名）
        
        Args:
            user_message: 用户消息
            system_message: 系统消息
            model_type: 模型类型
            
        Returns:
            模型回复的文本内容
        """
        return self.chat(user_message, system_message, model_type)
    
    def get_response_json(self, messages: List[Dict[str, Any]], model_type: str = "general") -> str:
        """
        获取完整的JSON响应
        
        Args:
            messages: 消息列表
            model_type: 模型类型
            
        Returns:
            JSON格式的响应字符串
        """
        model = self.get_model(model_type)
        completion = self.chat_completion(messages, model)
        return completion.model_dump_json()

    def _encode_image_to_base64(self, image_path: str) -> str:
        """
        将图片文件编码为Base64字符串

        Args:
            image_path: 图片文件的本地路径

        Returns:
            Base64编码的图片字符串
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            raise FileNotFoundError(f"图片文件未找到: {image_path}")
        except Exception as e:
            raise IOError(f"读取或编码图片时出错: {e}")

    def chat_with_image(self, text: str, image_input: str, model_type: str = "vision") -> str:
        """
        进行图文对话，支持图片URL或本地路径

        Args:
            text: 相关的文本
            image_input: 图片的URL或本地文件路径
            model_type: 模型类型

        Returns:
            模型回复的文本内容
        """
        model = self.get_model(model_type)
        
        image_url_data = {}
        # 判断是URL还是本地路径
        if image_input.startswith("http://") or image_input.startswith("https://"):
            image_url_data = {"url": image_input}
        else:
            # 假设是本地路径，进行Base64编码
            base64_image = self._encode_image_to_base64(image_input)
            # 根据文件扩展名确定MIME类型，这里简化处理
            image_format = image_input.split('.')[-1]
            if image_format.lower() in ['jpg', 'jpeg']:
                mime_type = "image/jpeg"
            elif image_format.lower() == 'png':
                mime_type = "image/png"
            else:
                # 默认或可以抛出错误
                mime_type = "image/jpeg" 
            image_url_data = {"url": f"data:{mime_type};base64,{base64_image}"}

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": image_url_data},
            ]
        }]
        completion = self.chat_completion(messages, model=model)
        return completion.choices[0].message.content

    def text_to_speech(self, text: str, save_path: str, voice: str = "Cherry", model_type: str = "tts") -> str:
        """
        将文本转换为语音并保存为音频文件

        Args:
            text: 要转换的文本
            save_path: 音频文件的保存路径
            voice: 使用的音色 (e.g., "Cherry")
            model_type: 模型类型

        Returns:
            成功保存文件的路径，如果失败则返回错误信息
        """
        model = self.get_model(model_type)

        try:
            response = dashscope.audio.qwen_tts.SpeechSynthesizer.call(
                model=model,
                api_key=self.api_key,
                text=text,
                voice=voice,
            )
            
            if response.output and "audio" in response.output and "url" in response.output.audio:
                audio_url = response.output.audio["url"]
            else:
                error_message = str(response)
                return f"TTS API调用失败，未返回有效的音频URL。响应: {error_message}"

            download_response = requests.get(audio_url)
            download_response.raise_for_status()

            with open(save_path, 'wb') as f:
                f.write(download_response.content)
            
            return f"音频文件已保存至：{save_path}"

        except Exception as e:
            return f"TTS处理失败：{str(e)}"