# XiaoFaSSH 部署指南（Linux）

- 环境要求：
  - Python 3.8+
  - pip / venv（推荐使用虚拟环境）
- 安装依赖（中国镜像）：
  - `python3 -m venv .venv && . .venv/bin/activate`
  - `pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
- 启动与端口：
  - 开发测试：`wssh --address=0.0.0.0 --port=8888`
  - 自定义端口：`wssh --address=0.0.0.0 --port=$PORT`
- 生产部署（示例 systemd）：
  - `/etc/systemd/system/xiaofa-ssh.service` 内容：
    ```
    [Unit]
    Description=XiaoFaSSH
    After=network.target

    [Service]
    WorkingDirectory=/opt/xiaofassh
    ExecStart=/opt/xiaofassh/.venv/bin/wssh --address=0.0.0.0 --port=8888
    Restart=always
    Environment=PYTHONUNBUFFERED=1

    [Install]
    WantedBy=multi-user.target
    ```
  - 运行：`sudo systemctl daemon-reload && sudo systemctl enable --now xiaofa-ssh`

- 端口与防火墙：
  - 开放对应端口（示例 8888），按云厂商/iptables/firewalld 规则自行放行。

- 依赖下载说明：
  - 默认使用中国镜像；如网络需要翻墙，请自行配置代理后再安装。

- 授权与开源声明：
  - 本项目基于 `https://github.com/huashengdun/webssh` 的 MIT 协议进行二次开发。
  - 除基础部分外，项目新增的 AI 智能体相关前端脚本（如 `static/js/main.js` 的 AI 逻辑）采用 Polyform Noncommercial License 1.0.0 授权：允许自用与非商业用途；商业使用需联系作者获取授权。
  - 如需商业授权，请联系：`yanghaopor`，邮箱:yanghao17308444882@gmail.com。

- 常见问题：
  - 启动卡住或无响应：可在页面点击“刷新SSH”按钮强制重连。
  - 视频背景加载失败：浏览器策略或网络原因，不影响功能；可刷新或改用静态图。