# -*- coding: utf-8 -*-
"""
BT4K影院 Spider
目标站: https://www.gmsanhe.com  (备用 yqk43.app)
架构:   苹果CMS  (分类/详情/搜索均为标准 maccms 风格)
适配:   继承 base.spider.Spider

======================================================================
重要: 该站启用 Cloudflare / CDN WAF，服务器/IP 直连会被 403。
       在本机(已通过浏览器验证的真人环境)运行时通常无需处理；
       若返回空列表，请按下方方式注入 cf_clearance cookie。

注入方式(任选其一):
  1) extend 参数: "cf_clearance=xxxx;host=https://www.gmsanhe.com"
  2) 环境变量:    export CF_CLEARANCE=xxxx
  3) 在同目录建  cookies.json : {"cf_clearance": "xxxx"}
======================================================================
"""

import os, re, json, urllib.parse
from bs4 import BeautifulSoup
import requests
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):

    # ---------- 初始化 ----------
    def init(self, extend=""):
        self.hosts = [
            "https://www.gmsanhe.com",
            "https://yqk43.app",
        ]
        self.host = self.hosts[0]
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }
        self.cookies = {}

        # 1) extend 字符串: cf_clearance=xxx;host=https://...
        if extend:
            for kv in extend.split(";"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k == "host":
                        self.host = v
                    elif k == "cf_clearance":
                        self.cookies["cf_clearance"] = v

        # 2) 环境变量
        cf = os.environ.get("CF_CLEARANCE")
        if cf and "cf_clearance" not in self.cookies:
            self.cookies["cf_clearance"] = cf

        # 3) cookies.json
        try:
            with open(os.path.join(os.path.dirname(__file__), "cookies.json"), "r") as f:
                for k, v in json.load(f).items():
                    self.cookies.setdefault(k, v)
        except Exception:
            pass

    def getName(self):
        return "BT4K影院"

    # ---------- 分类 & 筛选 ----------
    def homeContent(self, filter):
        return {
            "class": [
                # 电影
                {"type_id": "1",    "type_name": "电影"},
                {"type_id": "9736", "type_name": "动作片"},
                {"type_id": "12047","type_name": "喜剧片"},
                {"type_id": "4866", "type_name": "爱情片"},
                {"type_id": "2487", "type_name": "科幻片"},
                {"type_id": "7544", "type_name": "恐怖片"},
                {"type_id": "31706","type_name": "剧情片"},
                {"type_id": "1144", "type_name": "战争片"},
                {"type_id": "4011", "type_name": "纪录片"},
                {"type_id": "555",  "type_name": "悬疑片"},
                {"type_id": "457",  "type_name": "犯罪片"},
                {"type_id": "191",  "type_name": "奇幻片"},
                {"type_id": "3401", "type_name": "动画片"},
                {"type_id": "1115", "type_name": "预告片"},
                # 电视剧
                {"type_id": "2",    "type_name": "电视剧"},
                {"type_id": "12310","type_name": "国产剧"},
                {"type_id": "4455", "type_name": "港台剧"},
                {"type_id": "5488", "type_name": "日韩剧"},
                {"type_id": "11450","type_name": "欧美剧"},
                {"type_id": "2026", "type_name": "海外剧"},
                # 综艺 / 动漫 / 短剧
                {"type_id": "3",  "type_name": "综艺"},
                {"type_id": "4450","type_name": "大陆综艺"},
                {"type_id": "958", "type_name": "日韩综艺"},
                {"type_id": "4",  "type_name": "动漫"},
                {"type_id": "5",  "type_name": "短剧"},
            ],
            "filters": self._build_filters(),
        }

    def _build_filters(self):
        area = [{"n": a, "v": ("" if a == "全部" else a)} for a in
                ["全部", "大陆", "香港", "台湾", "美国", "韩国", "日本", "泰国",
                 "新加坡", "马来西亚", "印度", "英国", "法国", "加拿大",
                 "西班牙", "俄罗斯", "其它"]]
        year = [{"n": y, "v": ("" if y == "全部" else y)} for y in
                ["全部", "2026", "2025", "2024", "2023", "2022", "2021",
                 "2020", "2019", "2018", "2017", "2016", "2015", "2014",
                 "2013", "2012", "2011", "2010", "2009", "2008", "2007",
                 "2006", "2005", "2004"]]
        lang = [{"n": l, "v": ("" if l == "全部" else l)} for l in
                ["全部", "国语", "英语", "粤语", "闽南语", "韩语", "日语", "法语", "德语", "其它"]]
        sort = [{"n": "时间", "v": "time"}, {"n": "人气", "v": "hits"}, {"n": "评分", "v": "score"}]
        letter = [{"n": l, "v": ("" if l == "全部" else l)} for l in
                  ["全部"] + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["0-9"]]

        movie_genre = [{"n": v[0], "v": v[1]} for v in
                       [("全部",""),("喜剧","喜剧"),("爱情","爱情"),("恐怖","恐怖"),
                        ("动作","动作"),("科幻","科幻"),("剧情","剧情"),("战争","战争"),
                        ("警匪","警匪"),("犯罪","犯罪"),("动画","动画"),("奇幻","奇幻"),
                        ("武侠","武侠"),("冒险","冒险"),("枪战","枪战"),("悬疑","悬疑"),
                        ("惊悚","惊悚"),("经典","经典"),("青春","青春"),("文艺","文艺"),
                        ("微电影","微电影"),("古装","古装"),("历史","历史"),("运动","运动"),
                        ("农村","农村"),("儿童","儿童"),("网络电影","网络电影")]]
        tv_genre = [{"n": v[0], "v": v[1]} for v in
                    [("全部",""),("古装","古装"),("战争","战争"),("青春偶像","青春偶像"),
                     ("喜剧","喜剧"),("家庭","家庭"),("犯罪","犯罪"),("动作","动作"),
                     ("奇幻","奇幻"),("剧情","剧情"),("历史","历史"),("经典","经典"),
                     ("乡村","乡村"),("情景","情景"),("商战","商战"),("网剧","网剧"),
                     ("其他","其他")]]

        return {
            "1": [
                {"key": "class", "name": "类型",
                 "value": [{"n":"全部","v":"1"},{"n":"动作片","v":"9736"},{"n":"喜剧片","v":"12047"},
                           {"n":"爱情片","v":"4866"},{"n":"科幻片","v":"2487"},{"n":"恐怖片","v":"7544"},
                           {"n":"剧情片","v":"31706"},{"n":"战争片","v":"1144"},{"n":"纪录片","v":"4011"},
                           {"n":"悬疑片","v":"555"},{"n":"犯罪片","v":"457"},{"n":"奇幻片","v":"191"},
                           {"n":"动画片","v":"3401"},{"n":"预告片","v":"1115"}]},
                {"key": "genre", "name": "剧情", "value": movie_genre},
                {"key": "area", "name": "地区", "value": area},
                {"key": "year", "name": "年份", "value": year},
                {"key": "lang", "name": "语言", "value": lang},
                {"key": "letter", "name": "字母", "value": letter},
                {"key": "sort", "name": "排序", "value": sort},
            ],
            "2": [
                {"key": "class", "name": "类型",
                 "value": [{"n":"全部","v":"2"},{"n":"国产剧","v":"12310"},{"n":"港台剧","v":"4455"},
                           {"n":"日韩剧","v":"5488"},{"n":"欧美剧","v":"11450"},{"n":"海外剧","v":"2026"}]},
                {"key": "genre", "name": "剧情", "value": tv_genre},
                {"key": "area", "name": "地区", "value": area},
                {"key": "year", "name": "年份", "value": year},
                {"key": "lang", "name": "语言", "value": lang},
                {"key": "letter", "name": "字母", "value": letter},
                {"key": "sort", "name": "排序", "value": sort},
            ],
            "3": [
                {"key": "class", "name": "类型",
                 "value": [{"n":"全部","v":"3"},{"n":"大陆综艺","v":"4450"},{"n":"日韩综艺","v":"958"}]},
                {"key": "area", "name": "地区", "value": area},
                {"key": "year", "name": "年份", "value": year},
                {"key": "lang", "name": "语言", "value": lang},
                {"key": "sort", "name": "排序", "value": sort},
            ],
            "4": [
                {"key": "class", "name": "类型",
                 "value": [{"n":"全部","v":"4"},{"n":"国产动漫","v":"25"},{"n":"日韩动漫","v":"26"}]},
                {"key": "area", "name": "地区", "value": area},
                {"key": "year", "name": "年份", "value": year},
                {"key": "lang", "name": "语言", "value": lang},
                {"key": "sort", "name": "排序", "value": sort},
            ],
        }

    # ---------- 首页推荐 ----------
    def homeVideoContent(self):
        html = self._fetch("/")
        return {"list": self._parse_video_list(html)}

    # ---------- 分类列表 ----------
    def categoryContent(self, tid, pg, filter, extend):
        args = {}
        if extend and isinstance(extend, dict):
            for k, v in extend.items():
                if v: args[k] = str(v)
        if isinstance(filter, dict):
            for k, v in filter.items():
                if v and k not in args: args[k] = str(v)

        area   = args.get("area", "")
        genre  = args.get("genre", "")
        year   = args.get("year", "")
        lang   = args.get("lang", "")
        letter = args.get("letter", "")
        sort   = args.get("sort", "")

        # 无筛选 -> 标准分页
        if not any([area, genre, year, lang, letter, sort]):
            url = f"/list/{tid}--------{pg}.html"
            html = self._fetch(url)
            items = self._parse_video_list(html)
            pagecount = int(pg)
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.select("a"):
                t = a.get_text(" ", strip=True)
                if "尾页" in t or "末页" in t:
                    m = re.search(r"-(\d+)\.html", a.get("href", ""))
                    if m: pagecount = int(m.group(1))
                    break
            if not items: pagecount = 0
            return {"list": items, "page": int(pg), "pagecount": pagecount,
                    "limit": 36, "total": 9999}

        # 有筛选
        segs = [str(tid), area, year, letter, sort, "", "", "", ""]
        url = "/list/" + "-".join(segs) + ".html"
        html = self._fetch(url)
        items = self._parse_video_list(html)
        return {"list": items, "page": 1, "pagecount": 1, "limit": 36, "total": 9999}

    # ---------- 详情 ----------
    def detailContent(self, ids):
        result = {"list": []}
        vid = str(ids[0]).split(",")[0].strip()
        try:
            html = self._fetch(f"/detail/{vid}.html")
            if not html: return result
            soup = BeautifulSoup(html, "html.parser")

            vod_name = self._text(soup.select_one("h1") or soup.select_one("h2") or
                                   soup.select_one(".video-name") or soup.select_one(".slide-info-title"))
            vod_pic = ""
            img = soup.select_one("img.lazy, img.lazyload, .video-pic img, a.thumb img")
            if img:
                vod_pic = self._fix_pic(img.get("data-src") or img.get("src") or "")

            vod_director = vod_actor = vod_content = ""
            for el in soup.select(".slide-info, .video-info, .info p, .desc, .detail-info"):
                t = el.get_text(" ", strip=True)
                if not t: continue
                if t.startswith(("导演", "导演：")):
                    vod_director = re.split(r"[：:]", t, 1)[-1].strip()
                elif t.startswith(("主演", "演员", "主演：", "演员：")):
                    vod_actor = re.split(r"[：:]", t, 1)[-1].strip()
                elif t.startswith(("简介", "剧情", "描述", "简介：", "剧情：")):
                    vod_content = re.split(r"[：:]", t, 1)[-1].strip()
            if not vod_content:
                c = soup.select_one("#height_limit, .video-desc, .intro, .description, .summary")
                if c: vod_content = c.get_text(" ", strip=True)

            # 播放源
            play_from = []
            for tab in soup.select(".anthology-tab a, .play-tab a, .source-tab a, .tab-tag"):
                n = tab.get_text(" ", strip=True)
                if n: play_from.append(n)
            if not play_from: play_from.append("默认线路")

            tab_blocks = soup.select(".anthology-list-box, .play-list, .ep-list, .plist, ul.ep-list")
            play_url = []
            if tab_blocks:
                for i, block in enumerate(tab_blocks):
                    ep = []
                    for a in block.select("li a, a.episode"):
                        href = a.get("href", "")
                        m = re.search(r"/play/(.*?)\.html", href)
                        if m: ep.append(f"{a.text.strip()}${vid}-{m.group(1)}")
                    ep.reverse()
                    if ep and i < len(play_from): play_url.append("#".join(ep))
            else:
                ep = []
                for a in soup.select("a[href*='/play/']"):
                    m = re.search(r"/play/(.*?)\.html", a.get("href", ""))
                    if m: ep.append(f"{a.text.strip()}${vid}-{m.group(1)}")
                ep.reverse()
                if ep: play_url.append("#".join(ep))

            if not play_url: play_url.append("正片$default")

            valid_from = [pf for i, pf in enumerate(play_from) if i < len(play_url)]
            result["list"].append({
                "vod_id": vid, "vod_name": vod_name,
                "vod_pic": vod_pic, "vod_director": vod_director,
                "vod_actor": vod_actor, "vod_content": vod_content,
                "vod_play_from": "$$$".join(valid_from) or "默认线路",
                "vod_play_url": "$$$".join(play_url),
            })
        except Exception as e:
            print("[detailContent err]", e)
        return result

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg="1"):
        try: decoded = urllib.parse.unquote(key)
        except Exception: decoded = key
        q = urllib.parse.quote(decoded)
        html = self._fetch(f"/search?wd={q}&pg={pg}")
        items = self._parse_video_list(html)
        if not items:
            html2 = self._fetch(f"/search/{q}.html")
            items = self._parse_video_list(html2)
        return {"list": items, "page": int(pg), "pagecount": 1, "limit": 36, "total": len(items)}

    # ---------- 播放解析 ----------
    def playerContent(self, flag, id, vipFlags):
        url = ""
        try:
            if id.startswith("http"):
                url = id
            elif id == "default":
                return {"parse": 0, "url": "", "header": {}}
            else:
                url = f"{self.host}/play/{id}.html"

            html = self._fetch(url)
            if not html: return {"parse": 1, "url": url}

            # 1) player_aaaa json
            m = re.search(r"player_aaaa=(.*?)</script>", html, re.S)
            if m:
                try: pd = json.loads(m.group(1))
                except Exception: pd = {}
                play_url = pd.get("url", "")
                play_id  = pd.get("from", "")

                if play_url and play_url.startswith("http") and \
                        (play_url.endswith(".m3u8") or play_url.endswith(".mp4")):
                    return {"parse": 0, "url": play_url,
                            "header": {"User-Agent": self.headers["User-Agent"]}}

                # 2) 中转解析
                api_map = {
                    "YYNB": "https://zzrs.mfdyvip.com/player/mplayer.php",
                    "JD4K": "https://fgsrg.hzqingshan.com/player/mplayer.php",
                }
                api = api_map.get(play_id,
                                  "https://fgsrg.hzqingshan.com/player/mplayer.php")
                if play_url:
                    h2 = {
                        "User-Agent": self.headers["User-Agent"],
                        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                        "Referer": "https://www.gmsanhe.com/",
                        "Content-Type": "application/x-www-form-urlencoded",
                    }
                    try:
                        r2 = requests.get(f"https://fgsrg.hzqingshan.com/player/?url={play_url}",
                                          headers=h2, timeout=15)
                        tm = re.search(r'data-te="(.*?)"', r2.text)
                        if tm:
                            r3 = self.post(api, data={"url": play_url, "token": tm.group(1)},
                                           headers=h2)
                            r3.raise_for_status()
                            j = r3.json()
                            if j.get("code") == 200 and j.get("url"):
                                return {"parse": 0, "url": j["url"],
                                        "header": {"User-Agent": self.headers["User-Agent"]}}
                    except Exception as e:
                        print("[relay err]", e)

            # 3) 兜底: 直接抓 m3u8 / mp4
            for pat in [r"https?://[^\s'\"<>]+?\.m3u8", r"https?://[^\s'\"<>]+?\.mp4"]:
                mm = re.search(pat, html)
                if mm:
                    return {"parse": 0, "url": mm.group(0),
                            "header": {"User-Agent": self.headers["User-Agent"]}}
        except Exception as e:
            print("[playerContent err]", e)
        return {"parse": 1, "url": url}

    # ---------- 工具 / 占位 ----------
    def localProxy(self, param=""): return {}
    def isVideoFormat(self, url):
        return bool(url) and (url.endswith(".m3u8") or url.endswith(".mp4"))
    def manualVideoCheck(self): return False

    # ---------- 内部方法 ----------
    def _fetch(self, url):
        """带 host 切换 + cookie 注入的请求封装"""
        for host in [self.host] + [h for h in self.hosts if h != self.host]:
            try:
                full = url if url.startswith("http") else host + url
                rsp = self.fetch(full, headers=self.headers, cookies=self.cookies)
                text = rsp.text if rsp else ""
                if text and "Request denied" not in text and len(text) > 200:
                    self.host = host
                    return text
            except Exception as e:
                print(f"[fetch err][{host}] {e}")
        # 全失败 -> 裸请求便于排错
        try:
            full = url if url.startswith("http") else self.host + url
            r = requests.get(full, headers=self.headers, cookies=self.cookies, timeout=15)
            return r.text
        except Exception:
            return ""

    def _fix_pic(self, u):
        if not u: return ""
        if u.startswith("//"): return "https:" + u
        return u.replace("&amp;", "&")

    def _text(self, el):
        return el.get_text(" ", strip=True) if el else ""

    def _parse_video_list(self, html):
        videos, seen = [], set()
        if not html: return videos
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("a.public-list-exp, a.thumb, a.video-card, "
                            "a.thumb-txt, a[href*='/detail/']")
        for a in cards:
            href = a.get("href", "")
            m = re.search(r"/detail/(\d+)\.html", href)
            if not m: continue
            vid = m.group(1)
            if vid in seen: continue
            seen.add(vid)
            vod_name = (a.get("title", "")
                        or (a.select_one("img") and a.select_one("img").get("alt", ""))
                        or a.get_text(" ", strip=True))[:80]
            pic_el = a.select_one("img.lazy, img.lazyload, img")
            vod_pic = self._fix_pic((pic_el.get("data-src") or pic_el.get("src") or "")
                                     if pic_el else "")
            rem_el = a.select_one(".public-list-prb, .ft2, .remark, .ep, .info")
            vod_remarks = rem_el.get_text(" ", strip=True)[:40] if rem_el else ""
            videos.append({"vod_id": vid, "vod_name": vod_name.strip(),
                           "vod_pic": vod_pic, "vod_remarks": vod_remarks})
        return videos


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print("=== 首页分类 ===")
    print(json.dumps(sp.homeContent(True), ensure_ascii=False)[:500])
    # 取消注释以联调:
    # print(json.dumps(sp.categoryContent("1","1",True,{}), ensure_ascii=False)[:800])
    # print(json.dumps(sp.detailContent(["12345"]), ensure_ascii=False)[:1000])
    # print(json.dumps(sp.searchContent("锦绣未央", False), ensure_ascii=False)[:500])
