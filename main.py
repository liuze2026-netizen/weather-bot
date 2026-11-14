import os
import requests
import logging
from datetime import datetime, date

# 配置日志，方便在 GitHub Actions 中查看运行状态
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 从环境变量读取敏感信息（在 GitHub Secrets 中配置）
APPID = os.environ.get("WX_APPID", "你的appID")
SECRET = os.environ.get("WX_SECRET", "你的appsecret")
USERID = os.environ.get("WX_USERID", "你的userid")
TEMPLATE_ID = os.environ.get("WX_TEMPLATE_ID", "你的template_id")

# 经纬度，默认给个北京的，记得换成你的
LAT = os.environ.get("CITY_LAT", "39.90")
LON = os.environ.get("CITY_LON", "116.40")

# 恋爱纪念日，格式 YYYY-MM-DD
LOVE_DATE_STR = os.environ.get("LOVE_DATE", "2022-05-20")

# 天气代码映射 (WMO Weather interpretation codes)
WEATHER_CODES = {
    0: "晴朗",
    1: "大部晴朗", 2: "多云", 3: "阴天",
    45: "雾", 48: "沉积雾凇",
    51: "轻微毛毛雨", 53: "中度毛毛雨", 55: "浓密毛毛雨",
    56: "轻微冻雨", 57: "浓密冻雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "轻微冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    77: "雪粒",
    80: "小阵雨", 81: "中阵雨", 82: "强阵雨",
    85: "小阵雪", 86: "大阵雪",
    95: "雷阵雨", 96: "雷阵雨伴小冰雹", 99: "雷阵雨伴大冰雹"
}

def get_weather():
    """获取 Open-Meteo 天气数据"""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        current_weather = data.get("current_weather", {})
        temp = current_weather.get("temperature", "未知")
        code = current_weather.get("weathercode", -1)
        weather_desc = WEATHER_CODES.get(code, "未知天气")
        
        return weather_desc, temp
    except Exception as e:
        logging.error(f"获取天气失败: {e}")
        return "获取失败", "--"

def get_love_duration():
    """计算恋爱天数和周年数"""
    try:
        start_date = datetime.strptime(LOVE_DATE_STR, "%Y-%m-%d").date()
        today = date.today()
        
        # 1. 计算总天数
        days = (today - start_date).days + 1
        days = max(days, 0)
        
        # 2. 计算周年数
        years = today.year - start_date.year
        # 如果今年的纪念日还没到，年数减 1
        if (today.month, today.day) < (start_date.month, start_date.day):
            years -= 1
        years = max(years, 0)
        
        return days, years
    except Exception as e:
        logging.error(f"计算天数/年数失败: {e}")
        return 0, 0

def get_access_token():
    """获取微信 access_token"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if "access_token" in data:
            return data["access_token"]
        else:
            logging.error(f"获取 Token 失败: {data}")
            return None
    except Exception as e:
        logging.error(f"请求 Token 异常: {e}")
        return None

def send_wechat_msg(access_token, title, content):
    """发送模板消息"""
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    payload = {
        "touser": USERID,
        "template_id": TEMPLATE_ID,
        "data": {
            "title": {"value": title},
            "content": {"value": content}
        }
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if data.get("errcode") == 0:
            logging.info("消息推送成功！")
        else:
            logging.error(f"推送失败: {data}")
    except Exception as e:
        logging.error(f"发送消息异常: {e}")

def main():
    logging.info("开始执行推送任务...")
    
    # 1. 获取数据
    weather_desc, temp = get_weather()
    love_days, love_years = get_love_duration()
    
    logging.info(f"天气：{weather_desc}，温度：{temp}℃，恋爱：{love_days}天 ({love_years}周年)")
    
    # 2. 组装消息
    # 标题保持简短
    title = f"今日天气 & 恋爱第 {love_days} 天"
    
    # 内容里加上年数
    content = (
        f"今日天气：{weather_desc}\n"
        f"当前温度：{temp}℃\n"
        f"今天是我们相恋的第 {love_days} 天，也就是 {love_years} 周年。\n"
        f"继续好好爱彼此呀！❤️"
    )
    
    # 3. 获取 Token
    token = get_access_token()
    if not token:
        logging.error("因获取 Token 失败，任务提前结束。")
        return
        
    # 4. 发送推送
    send_wechat_msg(token, title, content)

if __name__ == "__main__":
    main()
