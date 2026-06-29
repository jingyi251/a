# -*- coding: utf-8 -*-
import re, urllib.parse
import json
from bs4 import BeautifulSoup
import requests
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://www.ht10010.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

    def getName(self):
        return '枫叶影院'

    def homeContent(self, filter):
        return {"class": [
            {'type_id': "/label/qq", 'type_name': "腾讯VIP精选"},
            {'type_id': "/label/bli", 'type_name': "B站VIP精选"},
            {'type_id': "/label/youku", 'type_name': "優酷VIP精选"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "5", "type_name": "热门短剧"},
        ], "filters": self._build_filters()}

    def _build_filters(self):
        area = [{"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"},
                {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "韩国", "v": "韩国"},
                {"n": "日本", "v": "日本"}, {"n": "泰国", "v": "泰国"}, {"n": "新加坡", "v": "新加坡"},
                {"n": "马来西亚", "v": "马来西亚"}, {"n": "印度", "v": "印度"}, {"n": "英国", "v": "英国"},
                {"n": "法国", "v": "法国"}, {"n": "加拿大", "v": "加拿大"}, {"n": "西班牙", "v": "西班牙"},
                {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "其它", "v": "其它"}]
        year = [{"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
                {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"},
                {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"},
                {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"},
                {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"}]
        lang = [{"n": "全部", "v": ""}, {"n": "国语", "v": "国语"}, {"n": "英语", "v": "英语"},
                {"n": "粤语", "v": "粤语"}, {"n": "闽南语", "v": "闽南语"}, {"n": "韩语", "v": "韩语"},
                {"n": "日语", "v": "日语"}, {"n": "法语", "v": "法语"}, {"n": "德语", "v": "德语"},
                {"n": "其它", "v": "其它"}]
        sort = [{"n": "时间", "v": "time"}, {"n": "人气", "v": "hits"}, {"n": "评分", "v": "score"}]
        letter = [{"n": "全部", "v": ""}, {"n": "A", "v": "A"}, {"n": "B", "v": "B"}, {"n": "C", "v": "C"},
                  {"n": "D", "v": "D"}, {"n": "E", "v": "E"}, {"n": "F", "v": "F"}, {"n": "G", "v": "G"},
                  {"n": "H", "v": "H"}, {"n": "I", "v": "I"}, {"n": "J", "v": "J"}, {"n": "K", "v": "K"},
                  {"n": "L", "v": "L"}, {"n": "M", "v": "M"}, {"n": "N", "v": "N"}, {"n": "O", "v": "O"},
                  {"n": "P", "v": "P"}, {"n": "Q", "v": "Q"}, {"n": "R", "v": "R"}, {"n": "S", "v": "S"},
                  {"n": "T", "v": "T"}, {"n": "U", "v": "U"}, {"n": "V", "v": "V"}, {"n": "W", "v": "W"},
                  {"n": "X", "v": "X"}, {"n": "Y", "v": "Y"}, {"n": "Z", "v": "Z"}, {"n": "0-9", "v": "0-9"}]
        return {
            "2": [
                {"key": "class", "name": "类型",
                 "value": [{"n": "全部", "v": "2"}, {"n": "国产剧", "v": "13"}, {"n": "日韩剧", "v": "15"},
                           {"n": "海外剧", "v": "16"}]},
                {"key": "area", "name": "地区", "value": area},
                {"key": "genre", "name": "剧情", "value": [{"n": v[0], "v": v[1]} for v in
                                                           [("全部", ""), ("古装", "古装"), ("战争", "战争"),
                                                            ("青春偶像", "青春偶像"), ("喜剧", "喜剧"),
                                                            ("家庭", "家庭"), ("犯罪", "犯罪"), ("动作", "动作"),
                                                            ("奇幻", "奇幻"), ("剧情", "剧情"), ("历史", "历史"),
                                                            ("经典", "经典"), ("乡村", "乡村"), ("情景", "情景"),
                                                            ("商战", "商战"), ("网剧", "网剧"), ("其他", "其他")]]},
                {"key": "year", "name": "年份", "value": year},
                {"key": "lang", "name": "语言", "value": lang},
                {"key": "letter", "name": "字母", "value": letter},
                {"key": "sort", "name": "排序", "value": sort},
            ],
            "1": [
                {"key": "class", "name": "类型",
                 "value": [{"n": "全部", "v": "1"}, {"n": "动作片", "v": "6"}, {"n": "喜剧片", "v": "7"},
                           {"n": "恐怖片", "v": "8"}, {"n": "科幻片", "v": "9"}, {"n": "爱情片", "v": "10"},
                           {"n": "剧情片", "v": "11"}, {"n": "战争片", "v": "12"}, {"n": "纪录片", "v": "20"}]},
                {"key": "area", "name": "地区", "value": area},
                {"key": "genre", "name": "剧情", "value": [{"n": v[0], "v": v[1]} for v in
                                                           [("全部", ""), ("喜剧", "喜剧"), ("爱情", "爱情"),
                                                            ("恐怖", "恐怖"), ("动作", "动作"), ("科幻", "科幻"),
                                                            ("剧情", "剧情"), ("战争", "战争"), ("警匪", "警匪"),
                                                            ("犯罪", "犯罪"), ("动画", "动画"), ("奇幻", "奇幻"),
                                                            ("武侠", "武侠"), ("冒险", "冒险"), ("枪战", "枪战"),
                                                            ("悬疑", "悬疑"), ("惊悚", "惊悚"), ("经典", "经典"),
                                                            ("青春", "青春"), ("文艺", "文艺"), ("微电影", "微电影"),
                                                            ("古装", "古装"), ("历史", "历史"), ("运动", "运动"),
                                                            ("农村", "农村"), ("儿童", "儿童"),
                                                            ("网络电影", "网络电影")]]},
                {"key": "year", "name": "年份", "value": year},
                {"key": "lang", "name": "语言", "value": lang},
                {"key": "letter", "name": "字母", "value": letter},
                {"key": "sort", "name": "排序", "value": sort},
            ],
            "4": [
                {"key": "class", "name": "类型",
                 "value": [{"n": "全部", "v": "4"}, {"n": "国产动漫", "v": "25"}, {"n": "日韩动漫", "v": "26"}]},
                {"key": "genre", "name": "剧情", "value": [{"n": v[0], "v": v[1]} for v in
                                                           [("全部", ""), ("情感", "情感"), ("科幻", "科幻"),
                                                            ("热血", "热血"), ("推理", "推理"), ("搞笑", "搞笑"),
                                                            ("冒险", "冒险"), ("奇幻", "奇幻"), ("战斗", "战斗"),
                                                            ("校园", "校园"), ("萝莉", "萝莉"), ("治愈", "治愈"),
                                                            ("原创", "原创"), ("亲子", "亲子"), ("益智", "益智"),
                                                            ("励志", "励志"), ("其他", "其他")]]},
                {"key": "area", "name": "地区",
                 "value": [{"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"},
                           {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "韩国", "v": "韩国"},
                           {"n": "日本", "v": "日本"}, {"n": "法国", "v": "法国"}, {"n": "英国", "v": "英国"},
                           {"n": "其它", "v": "其它"}]},
                {"key": "year", "name": "年份", "value": year},
                {"key": "lang", "name": "语言", "value": lang},
                {"key": "letter", "name": "字母", "value": letter},
                {"key": "sort", "name": "排序", "value": sort},
            ],
            "3": [
                {"key": "class", "name": "类型",
                 "value": [{"n": "全部", "v": "3"}, {"n": "大陆综艺", "v": "21"}, {"n": "日韩综艺", "v": "22"}]},
                {"key": "genre", "name": "剧情", "value": [{"n": v[0], "v": v[1]} for v in
                                                           [("全部", ""), ("选秀", "选秀"), ("情感", "情感"),
                                                            ("访谈", "访谈"), ("播报", "播报"), ("音乐", "音乐"),
                                                            ("美食", "美食"), ("旅游", "旅游"), ("搞笑", "搞笑"),
                                                            ("游戏", "游戏"), ("亲子", "亲子"), ("其它", "其它")]]},
                {"key": "area", "name": "地区",
                 "value": [{"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"},
                           {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "韩国", "v": "韩国"},
                           {"n": "日本", "v": "日本"}, {"n": "英国", "v": "英国"}, {"n": "其它", "v": "其它"}]},
                {"key": "year", "name": "年份", "value": year},
                {"key": "lang", "name": "语言", "value": lang},
                {"key": "letter", "name": "字母", "value": letter},
                {"key": "sort", "name": "排序", "value": sort},
            ],
        }

    def homeVideoContent(self):
        # 首页推荐：抓取首页 + 电影分类前几行作为推荐内容
        html = self._fetch('/')
        items = self._parse_video_list(html)
        # 如果首页内容不够，补充电影分类第一页
        if len(items) < 12:
            html2 = self._fetch('/cupfox-list/1---------.html')
            items2 = self._parse_video_list(html2)
            seen = set(it['vod_id'] for it in items)
            for it in items2:
                if it['vod_id'] not in seen:
                    items.append(it)
                    seen.add(it['vod_id'])
        return {"list": items[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        if tid.startswith('/label'):
            url = f'{tid}/page/{pg}.html'
            html = self._fetch(url)
            items = self._parse_video_list(html)
            page = int(pg)
            page_count = page if len(items) < 24 else page + 2
            return {"list": items, "page": page, "pagecount": page_count, "limit": 24, "total": page_count * 24}

        args = {}
        if extend and isinstance(extend, dict):
            for k, v in extend.items():
                if v:
                    args[k] = str(v)
        if isinstance(filter, dict):
            for k, v in filter.items():
                if v and k not in args:
                    args[k] = str(v)
        route_tid = args.get('class', args.get('tid', str(tid)))
        area = args.get('area', '')
        genre = args.get('genre', '')
        year = args.get('year', '')
        lang = args.get('lang', '')
        letter = args.get('letter', '')
        sort = args.get('sort', '')

        has_filter = bool(area or genre or year or lang or letter or sort)

        if not has_filter:
            # 无筛选：标准9段格式，分页通过末尾段承载
            url = f'/cupfox-list/{route_tid}---------{pg}.html'
            html = self._fetch(url)
            items = self._parse_video_list(html)
            page = int(pg)
            soup = BeautifulSoup(html, 'html.parser') if html else None
            pagecount = page
            if soup:
                for a in soup.select('a.page-link'):
                    if a.text.strip() == '尾页':
                        href = a.get('href', '')
                        m = re.search(r'---(\d+)---', href)
                        if not m:
                            m = re.search(r'/(\d+)\.html', href)
                        if m:
                            pagecount = int(m.group(1))
                        break
            if not items:
                pagecount = 0
            return {"list": items, "page": page, "pagecount": pagecount, "limit": 36, "total": pagecount * 36}

        # 有筛选：构建9段URL，支持分页
        segs = [route_tid, area, sort, genre, lang, letter, '', '', year]
        url = '/cupfox-list/' + '-'.join(segs) + f'---{pg}.html'
        html = self._fetch(url)
        items = self._parse_video_list(html)
        page = int(pg)
        soup = BeautifulSoup(html, 'html.parser') if html else None
        pagecount = page
        if soup:
            for a in soup.select('a.page-link'):
                if a.text.strip() == '尾页':
                    href = a.get('href', '')
                    m = re.search(r'---(\d+)---', href)
                    if not m:
                        m = re.search(r'/(\d+)\.html', href)
                    if m:
                        pagecount = int(m.group(1))
                    break
        if not items:
            pagecount = 0
        return {"list": items, "page": page, "pagecount": max(pagecount, 1), "limit": 36, "total": pagecount * 36}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0].split(',')[0].strip()
        try:
            html = self._fetch(f'/detail/{vid}.html')
            if not html:
                return result
            soup = BeautifulSoup(html, 'html.parser')

            # 标题 - 尝试多种选择器
            vod_name = ''
            for sel in ['h3.slide-info-title', '.detail-title', 'h1.title', '.video-name', '.vod-name']:
                el = soup.select_one(sel)
                if el and el.text.strip():
                    vod_name = el.text.strip()
                    break

            # 图片
            vod_pic = ''
            for sel in ['img.lazy', 'img.thumb', 'img.poster', 'img.cover', 'img']:
                el = soup.select_one(sel)
                if el:
                    src = el.get('data-src') or el.get('src') or ''
                    if src:
                        vod_pic = self._fix_pic(src)
                        break

            # 导演 / 演员
            vod_director = ''
            vod_actor = ''
            info_selectors = ['.slide-info', '.detail-info', '.video-info', '.info-item', '.vod-info']
            for sel in info_selectors:
                for el in soup.select(sel):
                    text = el.get_text(' ').strip()
                    if ('导演' in text or '導演' in text) and not vod_director:
                        vod_director = text.replace('导演：', '').replace('导演:', '').replace('導演：', '').strip()
                    elif ('演员' in text or '主演' in text or '演員' in text) and not vod_actor:
                        vod_actor = text.replace('演员：', '').replace('演员:', '').replace('主演:', '').replace('主演：', '').replace('演員：', '').strip()

            # 简介
            vod_content = ''
            for sel in ['#height_limit', '.detail-desc', '.video-desc', '.intro', '.description', '.vod-desc']:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    vod_content = el.get_text(' ', strip=True)
                    break

            # 播放源 & 剧集列表
            play_from, play_url = [], []

            tab_sels = ['.anthology-tab a.swiper-slide', '.play-tabs a', '.source-tab a', '.tab-item', '.line-tab a']
            tabs = []
            for ts in tab_sels:
                tabs = soup.select(ts)
                if tabs:
                    break
            for tab in tabs:
                src_name = tab.get_text(' ', strip=True).strip()
                if src_name:
                    play_from.append(src_name)

            block_sels = ['.anthology-list-box', '.play-list', '.episode-list', '.list-box', '.anthology-box']
            blocks = []
            for bs in block_sels:
                blocks = soup.select(bs)
                if blocks:
                    break

            if not blocks:
                # 兜底：直接找播放链接
                all_links = soup.select('a[href*="/play/"]')
                if all_links:
                    ep_list = []
                    for a in all_links:
                        href = a.get('href', '')
                        m = re.search(r'/play/(.*?)\.html', href)
                        if m:
                            ep_list.append(f'{a.text.strip()}${vid}-{m.group(1)}')
                    if ep_list:
                        play_url.append('#'.join(ep_list))
                        if not play_from:
                            play_from.append('默认线路')

            for i, block in enumerate(blocks):
                ep_list = []
                for a in block.select('li a, a.episode, .item a'):
                    href = a.get('href', '')
                    m = re.search(r'/play/(.*?)\.html', href)
                    if m:
                        ep_list.append(f'{a.text.strip()}${vid}-{m.group(1)}')
                if ep_list:
                    ep_list.reverse()
                    play_url.append('#'.join(ep_list))

            # 补齐 play_from
            while len(play_from) < len(play_url):
                play_from.append(f'线路{len(play_from) + 1}')

            valid_from = [pf for i, pf in enumerate(play_from) if i < len(play_url)]
            result["list"].append({
                "vod_id": vid, "vod_name": vod_name, "vod_pic": vod_pic,
                "vod_director": vod_director, "vod_actor": vod_actor,
                "vod_content": vod_content,
                "vod_play_from": "$$$".join(valid_from),
                "vod_play_url": "$$$".join(play_url),
            })
        except Exception as e:
            print(f"detailContent error: {e}")
        return result

    def searchContent(self, key, quick, pg="1"):
        try:
            decoded = urllib.parse.unquote(key)
        except:
            decoded = key
        encoded = urllib.parse.quote(decoded)
        # 搜索URL格式: /cupfox-search/query---------.html (9段)
        url = f'/cupfox-search/{encoded}---------{pg}.html'
        html = self._fetch(url)
        items = self._parse_search_list(html)
        # 尝试获取总页数
        soup = BeautifulSoup(html, 'html.parser') if html else None
        pagecount = 1
        if soup:
            for a in soup.select('a.page-link'):
                if a.text.strip() == '尾页':
                    href = a.get('href', '')
                    m = re.search(r'---(\d+)---', href)
                    if not m:
                        m = re.search(r'/(\d+)\.html', href)
                    if m:
                        pagecount = int(m.group(1))
                    break
        if not items and pagecount == 1:
            pagecount = 0
        return {"list": items, "page": int(pg), "pagecount": pagecount, "limit": 36, "total": pagecount * 36}

    def playerContent(self, flag, id, vipFlags):
        url = ''
        try:
            url = id if id.startswith('http') else f'{self.host}/play/{id}.html'
            html = self._fetch(url)
            if html:
                m = re.search(r'player_aaaa=(.*?)</script>', html, re.S)
                if m:
                    try:
                        pd = json.loads(m.group(1))
                    except Exception as e:
                        print(f"playerContent json error: {e}")
                        pd = {}

                    play_url = pd.get('url')
                    play_id = pd.get('from')

                    api_map = {
                        'YYNB': 'https://zzrs.mfdyvip.com/player/mplayer.php',
                        'JD4K': 'https://fgsrg.hzqingshan.com/player/mplayer.php',
                    }

                    if not play_url:
                        return {"parse": 0, "url": 'https://php.doube.eu.org/error.m3u8',
                                "header": {'User-Agent': 'Mozilla/5.0'}}

                    if play_url.startswith('http') and (play_url.endswith('.m3u8') or play_url.endswith('.mp4')):
                        return {"parse": 0, "url": play_url, "header": {'User-Agent': 'Mozilla/5.0'}}

                    # 需要二次解析
                    headers = {
                        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                        'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                        'Accept-Language': "zh-CN,zh;q=0.9",
                        'Cache-Control': "no-cache",
                        'Pragma': "no-cache",
                        'Referer': "https://www.ht10010.com/",
                        'Content-Type': 'application/x-www-form-urlencoded',
                    }
                    try:
                        resp = requests.get(f"https://fgsrg.hzqingshan.com/player/?url={play_url}", headers=headers, timeout=15)
                        token = re.search(r'data-te="(.*?)"', resp.text)
                        if token:
                            token_val = token.group(1)
                            payload = {'url': play_url, 'token': token_val}
                            api_url = api_map.get(play_id, 'https://fgsrg.hzqingshan.com/player/mplayer.php')
                            resp2 = self.post(api_url, data=payload, headers=headers, timeout=15)
                            resp2.raise_for_status()
                            result = resp2.json()
                            if result.get('code') == 200 and 'url' in result:
                                return {"parse": 0, "url": result['url'], "header": {
                                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'}}
                    except Exception as e:
                        print(f"playerContent parse error: {e}")

            return {"parse": 1, "url": url}
        except Exception as e:
            print(f"playerContent error: {e}")
        return {"parse": 1, "url": url}

    def localProxy(self, param=''):
        return {}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _fetch(self, url):
        try:
            if not url.startswith('http'):
                url = self.host + url
            rsp = self.fetch(url, headers=self.headers, timeout=15)
            if rsp and rsp.status_code == 200:
                return rsp.text
            elif rsp:
                print(f"_fetch: {url} => status {rsp.status_code}")
            return ''
        except Exception as e:
            print(f"_fetch error: {e}")
            return ''

    def _fix_pic(self, u):
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.host + u
        return u.replace('&amp;', '&')

    def _parse_video_list(self, html):
        videos, seen = [], set()
        soup = BeautifulSoup(html, 'html.parser')

        # 尝试多种卡片选择器
        cards = soup.select('a.public-list-exp')
        if not cards:
            cards = soup.select('a[href*="/detail/"]')
        if not cards:
            cards = soup.select('.video-item a, .vod-item a, .list-item a, .public-list a')

        for a in cards:
            href = a.get('href', '')
            m = re.search(r'/detail/(\d+)\.html', href)
            if not m:
                continue
            vod_id = m.group(1)
            if vod_id in seen:
                continue
            seen.add(vod_id)

            # 标题
            vod_name = (a.get('title', '') or '').strip()
            if not vod_name:
                img = a.select_one('img')
                if img:
                    vod_name = (img.get('alt', '') or '').strip()
            if not vod_name:
                txt = a.get_text(strip=True)
                if txt:
                    vod_name = txt[:50]

            # 图片
            pic_el = a.select_one('img')
            vod_pic = self._fix_pic(pic_el.get('data-src') or pic_el.get('src') or '') if pic_el else ''

            # 备注
            remark_el = a.select_one('.ft2') or a.select_one('.public-list-prb') or \
                         a.select_one('.video-remarks') or a.select_one('.remarks') or \
                         a.select_one('.public-prt')
            vod_remarks = remark_el.text.strip() if remark_el else ''

            # 年份/分类标签
            span = ','.join([sp.text for sp in a.select('span.public-prt, .tag, .label')])

            videos.append({
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_remarks": vod_remarks,
                "vod_year": span,
            })
        return videos

    def _parse_search_list(self, html):
        videos, seen = [], set()
        soup = BeautifulSoup(html, 'html.parser')

        cards = soup.select('a.public-list-exp')
        if not cards:
            cards = soup.select('a[href*="/detail/"]')
        if not cards:
            cards = soup.select('.video-item a, .vod-item a, .search-item a')

        for a in cards:
            href = a.get('href', '')
            m = re.search(r'/detail/(\d+)\.html', href)
            if not m:
                continue
            vod_id = m.group(1)
            if vod_id in seen:
                continue
            seen.add(vod_id)

            pic_el = a.select_one('img')
            vod_pic = self._fix_pic(pic_el.get('data-src') or pic_el.get('src') or '') if pic_el else ''

            # 搜索结果标题 - 尝试多种选择器
            vod_name = ''
            for sel in [f'a.thumb-txt[href="/detail/{vod_id}.html"]', '.thumb-txt', '.video-name', '.title', '.vod-name']:
                el = soup.select_one(sel)
                if el and el.text.strip():
                    vod_name = el.text.strip()
                    break
            if not vod_name:
                img = a.select_one('img')
                if img:
                    vod_name = (img.get('alt', '') or '').strip()
            if not vod_name:
                vod_name = (a.get('title', '') or '').strip()

            remark_el = a.select_one('.public-list-prb') or a.select_one('.ft2') or \
                         a.select_one('.video-remarks') or a.select_one('.remarks')
            vod_remarks = remark_el.text.strip() if remark_el else ''

            videos.append({
                "vod_id": vod_id,
                "vod_name": vod_name.strip(),
                "vod_pic": vod_pic,
                "vod_remarks": vod_remarks,
            })
        return videos


if __name__ == '__main__':
    sp = Spider()
    sp.init()
    print(sp.categoryContent('/label/qq', '1', True, {}))

