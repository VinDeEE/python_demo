# -*- coding: utf-8 -*-

# 导入 json 模块：用于把模型返回的 JSON 字符串解析成 Python 字典
import json
# 导入 os 模块：用于读取环境变量
import os
# 导入 sys 模块：用于向标准错误输出信息、退出程序
import sys
# 从 pathlib 导入 Path：用于跨平台处理文件路径
from pathlib import Path

# 从 openai SDK 导入 OpenAI 客户端（这里用于阿里 DashScope 的兼容接口）
from openai import OpenAI


# 定义函数：读取项目根目录 .env 文件，并把内容放进环境变量
def load_env_file() -> None:
    # 函数文档字符串：说明函数用途
    """从项目根目录读取 .env，并加载 key=value 配置。"""
    # 计算 .env 的绝对路径：当前文件 -> 上一级(course_one) -> 再上一级(项目根)
    env_file = Path(__file__).resolve().parent.parent / ".env"
    # 如果 .env 不存在，直接结束函数
    if not env_file.exists():
        return

    # 读取 .env 全文（UTF-8）并按行拆分，然后逐行处理
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        # 去掉行首行尾空白字符（空格、制表符、换行）
        line = raw_line.strip()
        # 跳过三类无效行：空行、注释行、没有等号的行
        if not line or line.startswith("#") or "=" not in line:
            continue

        # 用第一个 "=" 把字符串拆成 key 和 value 两部分
        key, value = line.split("=", 1)
        # 写入环境变量（仅当该 key 之前不存在时才写入）
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# 定义工具函数：返回城市天气（当前是演示版，不查真实天气）
def get_weather(city: str) -> str:
    # 函数文档字符串：说明入参和功能
    """查询指定城市天气（演示数据）。"""
    # 返回中文天气文案（f-string 会把 city 变量替换进去）
    return f"{city}天气晴朗。"


# 执行 .env 加载，让后续代码能读取 DASHSCOPE_API_KEY
load_env_file()

# 从环境变量读取阿里 DashScope Key
api_key = os.getenv("DASHSCOPE_API_KEY")
# 如果没有 key，就报错并退出（退出码 1 表示异常）
if not api_key:
    print("缺少 DASHSCOPE_API_KEY，请在环境变量或 .env 中配置。", file=sys.stderr)
    raise SystemExit(1)

# 创建 OpenAI 客户端，并指定 DashScope 的 OpenAI 兼容接口地址
client = OpenAI(
    # 传入你配置好的 key
    api_key=api_key,
    # 指定阿里兼容接口 base_url
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 组织对话消息列表：先给系统提示，再给用户问题
messages = [
    # system 角色：规定模型行为
    {
        # 角色字段固定为 system
        "role": "system",
        # 内容字段：告诉模型“有工具结果就直接输出工具结果，且用中文”
        "content": (
            "你是一个天气助手。"
            "当拿到工具结果时，只输出工具结果原文，并使用中文。"
        ),
    },
    # user 角色：用户真实问题
    {"role": "user", "content": "请查询中国武汉的天气，并用中文回答。"},
]

# 定义可用工具（函数调用协议）：告诉模型它可以调用 get_weather
tools = [
    # 列表中的第一个工具对象
    {
        # 工具类型是 function（函数）
        "type": "function",
        # 具体函数描述
        "function": {
            # 函数名：需要和你本地要执行的函数名对应
            "name": "get_weather",
            # 函数说明：给模型看的自然语言描述
            "description": "查询指定城市天气。",
            # 参数 JSON Schema：告诉模型参数结构
            "parameters": {
                # 参数整体类型是对象
                "type": "object",
                # 对象属性定义
                "properties": {
                    # city 参数定义
                    "city": {
                        # 参数类型是字符串
                        "type": "string",
                        # 参数说明
                        "description": "城市名，例如中国武汉。",
                    }
                },
                # 必填参数列表
                "required": ["city"],
                # 不允许额外字段
                "additionalProperties": False,
            },
        },
    }
]

# 第一次调用模型：让模型决定是否调用工具
first_response = client.chat.completions.create(
    # 指定模型
    model="qwen3.5-plus",
    # 传入当前消息
    messages=messages,
    # 传入工具定义
    tools=tools,
    # auto 表示让模型自动决定是否调工具
    tool_choice="auto",
)

# 取出第一条候选回复中的 message 对象
first_message = first_response.choices[0].message
# 如果模型没有发起工具调用，直接打印文本并正常结束
if not first_message.tool_calls:
    print(first_message.content or "")
    raise SystemExit(0)

# 准备一个列表：记录 assistant 这次发起的 tool_calls（要回传给模型）
assistant_tool_calls = []
# 准备一个列表：记录工具执行结果（role=tool 消息）
tool_results = []

# 遍历模型发起的每一个工具调用
for tool_call in first_message.tool_calls:
    # 如果不是我们支持的 get_weather，就跳过
    if tool_call.function.name != "get_weather":
        continue

    # 把函数参数 JSON 字符串解析为字典（无参数时用空对象）
    args = json.loads(tool_call.function.arguments or "{}")
    # 读取 city 参数，若缺失则默认“中国武汉”
    city = args.get("city", "中国武汉")
    # 调用本地 Python 函数，拿到工具结果文本
    weather_result = get_weather(city)
    # 组装 assistant 的 tool_calls 信息（用于第二轮补全上下文）
    assistant_tool_calls.append(
        {
            "id": tool_call.id,
            "type": "function",
            "function": {
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments,
            },
        }
    )
    # 组装 tool 消息（把函数结果返回给模型）
    tool_results.append(
        {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": weather_result,
        }
    )

# 把 assistant 的 tool_calls 消息追加到消息列表
messages.append(
    {
        "role": "assistant",
        "content": first_message.content or "",
        "tool_calls": assistant_tool_calls,
    }
)
# 再把所有 tool 结果消息追加进去
messages.extend(tool_results)

# 第二次调用模型：让模型基于工具结果生成最终中文答复
final_response = client.chat.completions.create(
    # 同样使用 qwen3.5-plus
    model="qwen3.5-plus",
    # 传入“包含工具结果”的完整消息
    messages=messages,
)

# 打印最终回答内容（为空时打印空字符串，避免 None 报错）
print(final_response.choices[0].message.content or "")
