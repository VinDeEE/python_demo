import argparse
import os

import requests

try:
    # Tavily 仅用于景点搜索，不应影响天气功能运行
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


WEATHER_CODE_MAP_ZH = {
    0: "晴朗",
    1: "基本晴",
    2: "局部多云",
    3: "阴",
    45: "雾",
    48: "冻雾",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "浓毛毛雨",
    56: "小冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "小冻雨",
    67: "大冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "冰粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴大冰雹",
}


def weather_code_to_zh(weather_code: int) -> str:
    return WEATHER_CODE_MAP_ZH.get(weather_code, f"未知天气(code={weather_code})")


def get_weather(city: str) -> str:
    """
    通过 Open-Meteo API 查询真实天气信息。
    流程：城市名 -> 经纬度 -> 当前天气。
    """
    try:
        geo_resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "zh", "format": "json"},
            timeout=15,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        locations = geo_data.get("results") or []
        if not locations:
            return f"错误:未找到城市 `{city}`，请尝试更具体的名称。"

        location = locations[0]
        latitude = location["latitude"]
        longitude = location["longitude"]
        resolved_city = location.get("name", city)
        country_code = location.get("country_code", "")

        weather_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,apparent_temperature,"
                    "relative_humidity_2m,weather_code,wind_speed_10m"
                ),
                "timezone": "auto",
            },
            timeout=15,
        )
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()
        current = weather_data.get("current") or {}

        weather_code = current.get("weather_code")
        weather_desc = weather_code_to_zh(weather_code) if weather_code is not None else "未知"

        temperature = current.get("temperature_2m", "未知")
        apparent_temperature = current.get("apparent_temperature", "未知")
        humidity = current.get("relative_humidity_2m", "未知")
        wind_speed = current.get("wind_speed_10m", "未知")
        observed_time = current.get("time", "未知")

        return (
            f"{resolved_city}{f'({country_code})' if country_code else ''}当前天气:{weather_desc}，"
            f"气温{temperature}摄氏度，体感{apparent_temperature}摄氏度，"
            f"湿度{humidity}%，风速{wind_speed}公里/小时，观测时间{observed_time}"
        )

    except requests.exceptions.Timeout:
        return "错误:查询天气超时，请稍后再试。"
    except requests.exceptions.RequestException as e:
        return f"错误:查询天气时遇到网络问题 - {e}"
    except (KeyError, IndexError, ValueError) as e:
        return f"错误:解析天气数据失败，可能是城市名称无效 - {e}"


def get_attraction(city: str, weather: str) -> str:
    """
    根据城市和天气，使用 Tavily Search API 搜索并返回景点推荐。
    """
    if TavilyClient is None:
        return "错误:未安装 tavily 包，请先执行 `pip install tavily-python`。"

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "错误:未配置 TAVILY_API_KEY 环境变量。"

    tavily = TavilyClient(api_key=api_key)
    query = f"'{city}' 在'{weather}'天气下最值得去的旅游景点推荐及理由"

    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        if response.get("answer"):
            return response["answer"]

        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")

        if not formatted_results:
            return "抱歉，没有找到相关的旅游景点推荐。"

        return "根据搜索，为您找到以下信息:\n" + "\n".join(formatted_results)
    except Exception as e:
        return f"错误:执行 Tavily 搜索时出现问题 - {e}"


# 将所有工具函数放入一个字典，方便后续调用
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="查询城市实时天气。")
    parser.add_argument("city", nargs="?", default="武汉", help="城市名，例如: 武汉")
    args = parser.parse_args()
    print(get_weather(args.city))


if __name__ == "__main__":
    main()
