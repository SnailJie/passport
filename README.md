# Passport
Unified authentication and authorization management SSO system for SaintIC Org.


# LICENSE
MIT


## Environment
> 1. Python Version: 2.6, 2.7
> 2. Web Framework: Flask
> 3. Required Modules for Python
> 4. MySQL, Redis


## Usage

```
1. Requirement:
    1.0 yum install -y gcc gcc-c++ python-devel libffi-devel openssl-devel mysql-devel
    1.1 git clone https://github.com/staugur/passport
    1.2 pip install -r requirements.txt
    1.3 MySQL需要导入misc/passport.sql数据库文件

2. modify config.py or add environment variables(os.getenv key in the reference configuration item):
    2.1 修改GLOBAL全局配置项(主要是端口、日志级别)
    2.2 修改MODULES核心配置项账号认证模块的MYSQL信息
    2.3 修改PLUGINS插件配置项(主要是第三方登录)

3. run:
    3.1 python main.py        #开发模式
    3.2 sh online_gunicorn.sh #生产模式
```


## TODO
```
0. redis sid存登录时设备信息
1. 绑定邮箱手机、手机登录
2. 签到
3. 用户行为记录
4. 系统管理
5. 安全
```

## Design
![Design][1]

[1]: ./misc/sso.png
