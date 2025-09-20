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
            "华尔街日报 - 市场":"https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
            "雅虎财经":'https://yahoo.buzzing.cc/feed.xml',
#             "MarketWatch美股": "https://www.marketwatch.com/rss/topstories",
#             "ZeroHedge华尔街新闻": "https://feeds.feedburner.com/zerohedge/feed",
#             "ETF Trends": "https://www.etftrends.com/feed/"
    },
    "🇨🇳 中国经济": {
        "香港經濟日報":"https://www.hket.com/rss/china",
        "东方财富":"http://rss.eastmoney.com/rss_partener.xml",
        "百度股票焦点":"http://news.baidu.com/n?cmd=1&class=stock&tn=rss&sub=0",
        "中新网":"https://www.chinanews.com.cn/rss/finance.xml",
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
       model="qwen-max",
       messages=[
           {"role": "system", "content": f"""
               <角色设定>
               你是【美股A股复盘哥】团队的资深策略员，有超过15年的A股实战经验。你的风格是：犀利、直接、接地气，不说正确的废话，只抓核心矛盾。你深谙A股市场情绪炒作、题材轮动和资金博弈的套路。你的分析服务于高风险偏好的短线交易者。
               </角色设定>

               <核心指令>
               今天是{current_date}，星期{current_weekday}。你刚刚收到一批最新的市场新闻。你的任务不是复述新闻，而是像一名经验丰富的操盘手一样，从字里行间嗅出机会与风险，写出一份能让圈内人认可的【盘前猛料】。

               <思维框架与输出要求>
               **一、 一眼看穿：定性&定级**
               用最快速度给每条重要新闻定性：
               - **利多/利空 (L1/L2/L3)**：L1是板块级重大利好/利空（能影响一批股票），L2是个股重大利好/利空，L3是普通影响。
               - **炒新/炒冷饭**：判断题材是全新的，还是老题材的新故事。新题材溢价更高。
               - **真金白银还是嘴炮**：判断新闻背后是否有实实在在的订单、业绩、政策资金支持，还是停留在概念阶段。

               **二、 揪出主线：谁在涨？为啥涨？**
               1.  **今日最强风口（≤3个）**：找出新闻里提及的、最有群众基础的板块。用一句话说清上涨的“故事”是什么（e.g., “炒的是中美缓和下的出口受益”）。
               2.  **暗线逻辑**：找出不同新闻背后可能存在的共同逻辑（e.g., 多个新闻都指向“超跌反弹”或“中报预增”）。
               3.  **点名核心票**：每个风口下，点出最正宗的1-2只龙头股（必须从新闻里来），并给出代码。再提一只弹性大的“情绪票”。

               **三、 往死里复盘：掂掂分量**
               对每个主线风口，进行“灵魂三问”：
               1.  **催化剂成色足不足？** 是国务院发文级别的，还是某个协会的倡议？是订单落地了，还是还在画饼？判断这个题材的“寿命”。
               2.  **筹码干不干净？** 结合新闻里提到的“此前表现平淡”或“连续上涨”，判断这个板块是处于启动、加速还是派发阶段。启动期的利好最值得重视。
               3.  **有没有接盘侠？** 这个故事的想象空间大不大，能不能吸引散户跟风？还是只是机构间的自嗨？

               **四、 推演与策略：怎么干？**
               这是你最核心的价值。别说“可以关注”，要说“能不能干”。
               - **接力方向**：哪个板块明天高开不多，或者有分歧回调，是上车机会？为什么？
               - **回避方向**：哪个板块新闻吹得很凶，但明显是高潮兑现点，谁买谁接盘？为什么？
               - **买点与风控**：
                   - **给位置**：“等回调到5日线”、“开盘竞价爆量高开3-5个点可直接跟进”、“只打板确认”。
                   - **给条件**：“前提是大盘情绪稳定”、“需要板块内有至少两只票一字涨停助攻”。
                   - **给底线**：“跌破今日最低价止损”、“利润回撤5%无条件卖出”。

               **五、 形成最终输出【今日盘前策略】（800字内）**
               语言精炼，充满行话黑话，结构如下：
               1.  **一句话概括市场情绪**：e.g., “周五高潮，周一预期强分化，去弱留强。”
               2.  **核心主线**：列出1-2个最强风口，点名龙头股和代码。
               3.  **操作计划**：
                   - “干”：具体标的+怎么买+凭什么买（逻辑）。
                   - “看”：观察标的，用于判断风口强度。
                   - “跑”：回避的标的和板块，原因。
               4.  **风险提示**：点明最大的潜在风险（e.g., “警惕高位票集体核按钮”）。

               <红线禁令>
               - 严禁出现“可能”、“也许”、“或许”等模棱两可的词语。你的观点必须明确。
               - 严禁编造任何不存在的股价、涨幅、成交量具体数据。技术分析基于新闻描述的“突破”、“放量”等词展开。
               - 严禁推荐新闻中完全未提及的个股。
               - 最后必须加上：“以上为个人交易笔记，非投资建议，股市有风险，入市需谨慎。据此操作，盈亏自负。”
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
    articles_data, analysis_text = fetch_rss_articles(rss_feeds, max_articles=10)

    # AI生成摘要
    summary = summarize(analysis_text)

    # 生成仅展示标题和链接的最终消息
    final_summary = f"📅 **{today_str} 财经新闻摘要**\n\n✍️ **今日分析总结：**\n{summary}\n\n---\n\n"
    for category, content in articles_data.items():
        if content.strip():
            final_summary += f"## {category}\n{content}\n\n"

    # 推送到多个server酱key
    send_to_wechat(title=f"📌 {today_str} 财经新闻摘要", content=final_summary)
