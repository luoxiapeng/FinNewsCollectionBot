# 福生无量天尊
from openai import OpenAI
import feedparser
import requests
from newspaper import Article
from datetime import datetime
import time
import pytz
import os
# OpenAI API Key
# openai_api_key = os.getenv("OPENAI_API_KEY")
# 从环境变量获取 Server酱 SendKeys
server_chan_keys_env = os.getenv("SERVER_CHAN_KEYS")
if not server_chan_keys_env:
    raise ValueError("环境变量 SERVER_CHAN_KEYS 未设置，请在Github Actions中设置此变量！")
server_chan_keys = server_chan_keys_env.split(",")

# openai_client = OpenAI(api_key=openai_api_key, base_url="https://api.deepseek.com/v1")
# 获取DashScope API Key
dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
if not dashscope_api_key:
    raise ValueError("环境变量 DASHSCOPE_API_KEY 未设置，请在Github Actions中设置此变量！")

openai_client = OpenAI(
    api_key=dashscope_api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# RSS源地址列表
rss_feeds = {
    "📈 富途牛牛": {
        "富途牛牛市场资讯": {
            "url": "https://news.futunn.com/news-site-api/main/get-market-list?size=15",
            "type": "json"
        }
    },
    "📊 格隆汇": {
        "格隆汇财经": {
            "url": "https://www.gelonghui.com/api/live-channels/all/lives/v4?category=all&limit=15",
            "type": "json2"
        }
    },
    "💰智通财经": {
        "智通财经": {
            "url": "https://mapi.zhitongcaijing.com/news/list.html?mode=history&access_token=&category_id=index_shouye&category_key=&language=zh-cn&last_time=&page=1&tradition_chinese=0",
            "type": "json3"
        }
    },
    "🌐 金色财经": {
            "金色财经快讯": {
                "url": "https://api.jinse.cn/noah/v2/lives?limit=20&reading=false&source=web&flag=up&id=0&category=0",
                "type": "json4"
            }
      },
    "💲华尔街见闻":{
        "华尔街见闻":"https://dedicated.wallstreetcn.com/rss.xml",
    },
     "彭博社":{
          "彭博社":"https://bloombergnew.buzzing.cc/feed.xml"
     },
    "💻 36氪":{
        "36氪":"https://36kr.com/feed",
    },
    "财联社":{
          "财联社头条":' https://rsshub.app/cls/telegraph/red',
          "财联社热门":' https://rsshub.app/cls/hot'
    },
     "🇺🇸 美国经济": {
            "华尔街日报 - 经济":"https://cn.wsj.com/zh-hans/rss",
            "联合早报":"https://plink.anyfeeder.com/zaobao/realtime/world",
            "纽约时报":"https://plink.anyfeeder.com/nytimes/dual",
#             "华尔街日报 - 市场":"https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
            "雅虎财经":'https://yahoo.buzzing.cc/feed.xml',
#             "MarketWatch美股": "https://www.marketwatch.com/rss/topstories",
#             "ZeroHedge华尔街新闻": "https://feeds.feedburner.com/zerohedge/feed",
#             "ETF Trends": "https://www.etftrends.com/feed/"
    },
    "🇨🇳 中国经济": {
        "香港經濟日報":"https://www.hket.com/rss/china",
#         "东方财富":"http://rss.eastmoney.com/rss_partener.xml",
        "百度股票焦点":"http://news.baidu.com/n?cmd=1&class=stock&tn=rss&sub=0",
#         "中新网":"https://www.chinanews.com.cn/rss/finance.xml",
        "同花顺":"https://rsshub.app/10jqka/realtimenews"
    },

#     "🌍 世界经济": {
#         "华尔街日报 - 经济":"https://feeds.content.dowjones.io/public/rss/socialeconomyfeed",
#         "BBC全球经济": "http://feeds.bbci.co.uk/news/business/rss.xml",
#     },
}

# 获取北京时间
def today_date():
    return datetime.now(pytz.timezone("Asia/Shanghai")).date()

# 爬取网页正文 (用于 AI 分析，但不展示)
def fetch_article_text(url):
    try:
        print(f"📰 正在爬取文章内容: {url}")
        article = Article(url)
        article.download()
        article.parse()
        text = article.text[:1500]  # 限制长度，防止超出 API 输入限制
        if not text:
            print(f"⚠️ 文章内容为空: {url}")
        return text
    except Exception as e:
        print(f"❌ 文章爬取失败: {url}，错误: {e}")
        return "（未能获取文章正文）"

# 添加 User-Agent 头
def fetch_feed_with_headers(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    return feedparser.parse(url, request_headers=headers)

# 自动重试获取 RSS
def fetch_feed_with_retry(url, retries=3, delay=5):
    for i in range(retries):
        try:
            feed = fetch_feed_with_headers(url)
            if feed and hasattr(feed, 'entries') and len(feed.entries) > 0:
                return feed
        except Exception as e:
            print(f"⚠️ 第 {i+1} 次请求 {url} 失败: {e}")
            time.sleep(delay)
    print(f"❌ 跳过 {url}, 尝试 {retries} 次后仍失败。")
    return None

# 获取富途牛牛JSON接口内容
def fetch_json_articles(url, max_articles=20):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        articles = []
        analysis_text = ""

        # 解析JSON数据获取文章列表
        news_list = data.get('data', {}).get('list', [])

        for item in news_list[:max_articles]:
            title = item.get('title', '无标题')
            abstract = item.get('abstract', '')
            link = item.get('url', '')

            if not link:
                continue

            articles.append(f"- [{title}]({link})")

            # 使用标题和摘要作为AI分析的主要内容
            content_for_analysis = f"{title}\n{abstract}"
            analysis_text += f"【{title}】\n{content_for_analysis}\n\n"

        return articles, analysis_text

    except Exception as e:
        print(f"❌ 富途牛牛接口获取失败: {e}")
        return [], ""

# 获取格隆汇JSON接口内容
def fetch_gelonghui_articles(url, max_articles=20):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        articles = []
        analysis_text = ""

        # 解析JSON数据获取文章列表
        news_list = data.get('result', [])

        for item in news_list[:max_articles]:
            title = item.get('title', '').strip()
            content = item.get('content', '').strip()
            link = item.get('route', '').strip()

            # 如果标题、内容、链接都为空，则跳过
            if not title or not content or not link:
                continue

            articles.append(f"- [{title}]({link})")

            # 使用标题和内容作为AI分析的主要内容
            content_for_analysis = f"{title}\n{content}"
            analysis_text += f"【{title}】\n{content_for_analysis}\n\n"

        return articles, analysis_text

    except Exception as e:
        print(f"❌ 格隆汇接口获取失败: {e}")
        return [], ""


# 获取智通财经JSON接口内容
def fetch_zhitongcaijing_articles(url, max_articles=20):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        articles = []
        analysis_text = ""

        # 解析JSON数据获取文章列表
        news_list = data.get('data', {}).get('list', [])

        for item in news_list[:max_articles]:
            title = item.get('title', '无标题')
            digest = item.get('digest', '')
            url_path = item.get('url', '')

            # 构造完整链接
            if url_path:
                link = f"https://mapi.zhitongcaijing.com{url_path}"
            else:
                link = ""

            if not link:
                continue

            articles.append(f"- [{title}]({link})")

            # 使用标题和摘要作为AI分析的主要内容
            content_for_analysis = f"{title}\n{digest}"
            analysis_text += f"【{title}】\n{content_for_analysis}\n\n"

        return articles, analysis_text

    except Exception as e:
        print(f"❌ 智通财经接口获取失败: {e}")
        return [], ""

# 获取金色财经JSON接口内容
def fetch_jinse_articles(url, max_articles=20):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.jinse.cn/'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        articles = []
        analysis_text = ""

        # 解析JSON数据获取文章列表
        live_list = []
        if 'list' in data:
            # 按日期分组的数据结构
            for date_group in data['list']:
                if 'lives' in date_group:
                    live_list.extend(date_group['lives'])
        elif 'lives' in data:
            # 直接的lives列表
            live_list = data['lives']

        for item in live_list[:max_articles]:
            content = item.get('content', '无内容')
            link = item.get('link', '')
            id = item.get('id', '')

            if not content:
                continue

            # 如果没有链接，构造一个
            if not link and id:
                link = f"https://www.jinse.cn/news/detail/{id}.html"

            # 提取标题（使用内容的前30个字符作为标题）
            title = content[:30] + "..." if len(content) > 30 else content

            articles.append(f"- [{title}]({link})")

            # 使用内容作为AI分析的主要内容
            content_for_analysis = content
            analysis_text += f"【{title}】\n{content_for_analysis}\n\n"

        return articles, analysis_text

    except Exception as e:
        print(f"❌ 金色财经接口获取失败: {e}")
        return [], ""

# 获取RSS内容（爬取正文但不展示）
def fetch_rss_articles(rss_feeds, max_articles=10):
    news_data = {}
    analysis_text = ""  # 用于AI分析的正文内容

    for category, sources in rss_feeds.items():
        category_content = ""
        for source, source_info in sources.items():
            # 判断是RSS源还是JSON源
            if isinstance(source_info, dict) and source_info.get('type') == 'json':
                # 处理富途牛牛JSON接口源
                print(f"📡 正在获取 {source} 的 JSON 接口: {source_info['url']}")
                articles, analysis = fetch_json_articles(source_info['url'], 15)  # 富途牛牛固定获取15条
                analysis_text += analysis
                articles_content = ""
                if articles:
                    articles_content = f"### {source}\n" + "\n".join(articles) + "\n\n"
            elif isinstance(source_info, dict) and source_info.get('type') == 'json2':
                # 处理格隆汇JSON接口源
                print(f"📡 正在获取 {source} 的 JSON 接口: {source_info['url']}")
                articles, analysis = fetch_gelonghui_articles(source_info['url'], 15)  # 格隆汇固定获取15条
                analysis_text += analysis
                articles_content = ""
                if articles:
                    articles_content = f"### {source}\n" + "\n".join(articles) + "\n\n"
            elif isinstance(source_info, dict) and source_info.get('type') == 'json3':
                # 处理智通财经JSON接口源
                print(f"📡 正在获取 {source} 的 JSON 接口: {source_info['url']}")
                articles, analysis = fetch_zhitongcaijing_articles(source_info['url'], 10)  # 智通财经固定获取10条
                analysis_text += analysis
                articles_content = ""
                if articles:
                    articles_content = f"### {source}\n" + "\n".join(articles) + "\n\n"
            elif isinstance(source_info, dict) and source_info.get('type') == 'json4':
                # 处理金色财经JSON接口源
                print(f"📡 正在获取 {source} 的 JSON 接口: {source_info['url']}")
                articles, analysis = fetch_jinse_articles(source_info['url'], 20)  # 金色财经固定获取20条
                analysis_text += analysis
                articles_content = ""
                if articles:
                    articles_content = f"### {source}\n" + "\n".join(articles) + "\n\n"
            else:
                # 处理原有的RSS源
                url = source_info
                print(f"📡 正在获取 {source} 的 RSS 源: {url}")

                # 特殊处理华尔街见闻，获取10条新闻
                if source == "华尔街见闻":
                    feed_max_articles = 10
                else:
                    feed_max_articles = max_articles

                feed = fetch_feed_with_retry(url)
                if not feed:
                    print(f"⚠️ 无法获取 {source} 的 RSS 数据")
                    continue
                print(f"✅ {source} RSS 获取成功，共 {len(feed.entries)} 条新闻")

                articles = []  # 每个source都需要重新初始化列表
                for entry in feed.entries[:feed_max_articles]:
                    title = entry.get('title', '无标题')
                    link = entry.get('link', '') or entry.get('guid', '')
                    if not link:
                        print(f"⚠️ {source} 的新闻 '{title}' 没有链接，跳过")
                        continue

                    # 爬取正文用于分析（不展示）
                    article_text = fetch_article_text(link)
                    analysis_text += f"【{title}】\n{article_text}\n\n"

                    print(f"🔹 {source} - {title} 获取成功")
                    articles.append(f"- [{title}]({link})")

                articles_content = ""
                if articles:
                    articles_content = f"### {source}\n" + "\n".join(articles) + "\n\n"

            category_content += articles_content

        news_data[category] = category_content

    return news_data, analysis_text

# AI 生成内容摘要（基于爬取的正文）
def summarize(text):
    # 获取当前北京时间
    current_date = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d")
    current_weekday = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%A")

    completion = openai_client.chat.completions.create(
        model="qwen-max",  # 或其他你选择的模型
        messages=[
           {"role": "system", "content": f"""
          # 角色定位
          您是一名拥有10年经验的首席策略师，专注于中国股票市场的行业轮动与主题投资分析。您擅长从新闻文本中提取关键信号，并结合市场环境做出专业判断。

          # 分析背景
          当前日期：{current_date}，星期{current_weekday}
          数据来源：当日市场新闻与文本数据

          # 核心任务
          请基于以下结构化框架对提供的新闻内容进行专业分析：

          ## 1. 热点识别与主题提取
          - 识别新闻中涉及的主要行业/主题（按申万一级行业分类）
          - 筛选出近期（1-3天）具有动量效应的3个核心热点
          - 特别关注此前2周表现平淡但近期开始异动的潜在新热点

          ## 2. 新闻事件影响分析
          对每条重要新闻进行三维度评估：
          - 影响性质：利好/利空/中性（用▲/▼/●表示）
          - 影响程度：高/中/低（用⭐级表示）
          - 影响范围：个股层面/行业层面/市场层面
          - 最受影响的2-3个标的及简要逻辑

          ## 3. 深度分析框架（对每个重点行业/主题）
          ### 催化剂分析
          - 政策催化：产业政策、区域规划、行业规范
          - 数据催化：业绩超预期、行业数据亮眼
          - 事件催化：技术突破、订单落地、战略合作
          - 情绪催化：市场风险偏好变化、资金流向

          ### 行情复盘与逻辑梳理
          - 过去3个月行业/主题的核心驱动逻辑演变
          - 关键时间节点的市场表现（不要使用具体价格，用"显著跑赢/跑输大盘"等相对表述）
          - 当前所处阶段：启动期/加速期/分化期/退潮期

          ### 持续性展望
          基于以下维度判断热点可持续性：
          - 政策支持力度与持续性
          - 行业基本面改善程度
          - 资金介入深度（从新闻中推断）
          - 技术面位置（相对高低）

          ### 标的推荐
          - 龙头标的：2-3只最具代表性的个股
          - ETF选项：相关的行业ETF（如有）
          - 须包含标的代码和名称，按逻辑关联度排序

          ### 技术分析要点
          基于新闻中提到的技术信号：
          - 趋势状态：上升趋势/下降趋势/震荡整理
          - 关键位置：接近阻力位/支撑位/突破关键位置
          - 量价特征：放量上涨/缩量调整/量价背离
          - 形态特征：头肩底、双底、三角形整理等

          ### 操作建议
          提供具体的交易策略：
          - 理想买点：如"回调至前期支撑位附近"
          - 加仓条件：如"放量突破XX关键位置"
          - 止损参考：如"跌破XX重要支撑"
          - 持仓周期：短线（1-3天）/中线（1-2周）/长线（1月+）

          ## 4. 输出要求
          - 形成1500字以内的专业分析报告
          - 结构清晰：摘要→热点分析→个股聚焦→操作策略
          - 语言风格：专业、简洁、客观
          - 目标读者：机构投资者和专业交易员

          ## 5. 今日重点关注
          列出3-5个最值得关注的标的，每项包含：
          - 标的名称及代码
          - 关注理由（不超过20字）
          - 关键价位提示（如"关注突破机会"、"回调企稳机会"）
          - 风险等级：高/中/低

          # 重要注意事项
          1. 严禁编造或猜测具体股价数据
          2. 所有分析必须基于新闻文本提供的信息
          3. 技术分析要注明是基于文本中提到的技术信号
          4. 明确标注"市场有风险，投资需谨慎"
          5. 保持客观中立，避免过度乐观或悲观表述
             """},
            {"role": "user", "content": text}
        ]
    )
    return completion.choices[0].message.content.strip()

# 发送微信推送
def send_to_wechat(title, content):
    for key in server_chan_keys:
        url = f"https://sctapi.ftqq.com/{key}.send"
        data = {"title": title, "desp": content}
        response = requests.post(url, data=data, timeout=10)
        if response.ok:
            print(f"✅ 推送成功: {key}")
        else:
            print(f"❌ 推送失败: {key}, 响应：{response.text}")


if __name__ == "__main__":
    today_str = today_date().strftime("%Y-%m-%d")

    # 每个网站获取最多 5 篇文章（富途牛牛、格隆汇、智通财经和华尔街见闻除外）
    articles_data, analysis_text = fetch_rss_articles(rss_feeds, max_articles=7)

    # AI生成摘要
    summary = summarize(analysis_text)

    # 生成仅展示标题和链接的最终消息
    final_summary = f"📅 **{today_str} 财经新闻摘要**\n\n✍️ **今日分析总结：**\n{summary}\n\n---\n\n"
    for category, content in articles_data.items():
        if content.strip():
            final_summary += f"## {category}\n{content}\n\n"

    # 推送到多个server酱key
    send_to_wechat(title=f"📌 {today_str} 财经新闻摘要", content=final_summary)
