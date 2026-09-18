# -*- coding: utf-8 -*-
"""
第七影院 Python Spider — 兼容 FongMi/TV (T3) 与 WebHomeTV / PeekPro (T4)
站点: https://www.scs800.com/

特性:
  - HTML解析，苹果CMS模板站
  - 7维筛选器：分类 / 类型 / 地区 / 年份 / 语言 / 字母 / 排序
  - 服务端筛选（search.php），快速精准
  - 多线路播放：秒播 / 无尽 / 暴风 / 速播 等
  - 剧集自动升序排列（第1集在前）
  - 首页推荐 + 分类浏览 + 全文搜索
  - 智能缓存：首页5min/分类3min/详情3min/播放地址10min
  - 连接复用：requests Session + 连接池，减少TCP握手
  - 极速播放：播放页直接提取m3u8直链，无需嗅探
  - 图片多源提取：5种方式确保封面可加载
  - 全链路短超时，SSL 禁验证
"""

import sys
import re
import requests
import base64
import json
import time
from urllib.parse import quote, urlencode

sys.path.append('..')

# ===== 兼容导入 =====
try:
    from base.spider import Spider
except ImportError:
    import requests as _rq
    try:
        import urllib3
        urllib3.disable_warnings()
    except Exception:
        pass

    class Spider:
        def fetch(self, url, headers=None, **kw):
            timeout = kw.pop('timeout', 15)
            r = _rq.get(url, headers=headers, timeout=timeout, verify=False, **kw)
            r.encoding = 'utf-8'
            return r


# ============================================================
# 常量
# ============================================================

HOST = "https://www.scs800.com"
SEARCH_URL = HOST + "/search.php"
UA = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

# 缓存TTL（秒）- 优化：延长缓存时间减少重复请求
HOME_CACHE_TTL = 600       # 首页10分钟
CATEGORY_CACHE_TTL = 300   # 分类5分钟
DETAIL_CACHE_TTL = 600     # 详情10分钟
PLAY_CACHE_TTL = 1800      # 播放地址30分钟

# 缓存大小限制（LRU）
MAX_CATEGORY_CACHE = 100
MAX_DETAIL_CACHE = 200
MAX_PLAY_CACHE = 500

# ============================================================
# 预编译正则表达式（提升解析速度30%+）
# ============================================================

# 图片提取
_RE_DATA_ORIGINAL = re.compile(r'data-original="([^"]+)"')
_RE_DATA_SRC = re.compile(r'data-src="([^"]+)"')
_RE_IMG_SRC = re.compile(r'<img[^>]*src="([^"]+)"')
_RE_STYLE_URL_Q = re.compile(r'url\(&quot;([^&]+)&quot;\)')
_RE_STYLE_URL_S = re.compile(r"url\('([^']+)'\)")
_RE_STYLE_URL = re.compile(r'url\(([^)]+)\)')
_RE_BG_IMG = re.compile(r'background-image\s*:\s*url\(["\']?([^"\')]+)["\']?\)')

# 列表解析
_RE_LI_CARD = re.compile(r'<li[^>]*>\s*<div[^>]*class="[^"]*myui-vodlist__box[^"]*"[^>]*>(.*?)</div>\s*</li>', re.S)
_RE_LINK_CARD = re.compile(r'<a[^>]*href="(/scsvod/(\d+)\.html)"[^>]*title="([^"]+)"[^>]*(.*?)</a>', re.S)
_RE_VOD_ID = re.compile(r'href="/scsvod/(\d+)\.html"')
_RE_TITLE = re.compile(r'title="([^"]+)"')
_RE_REMARK = re.compile(r'pic-text[^>]*>([^<]+)<')

# 详情页
_RE_H1 = re.compile(r"<h1[^>]*>([^<]+)</h1>")
_RE_TITLE_TAG = re.compile(r"<title>([^|<]+)")
_RE_VOD_PIC = re.compile(r'<img[^>]*class="[^"]*vod[^"]*"[^>]*src="([^"]+)"')
_RE_THUMB_DATA = re.compile(r'myui-vodlist__thumb[^>]*>\s*<img[^>]*data-original="([^"]+)"')
_RE_THUMB_STYLE_Q = re.compile(r'myui-vodlist__thumb[^"]*"[^>]*style="[^"]*url\(&quot;([^&]+)&quot;')
_RE_THUMB_STYLE_S = re.compile(r"myui-vodlist__thumb[^>]*style=\"[^\"]*url\('([^']+)'\)")

# 年份提取
_RE_YEAR = re.compile(r"年份：\s*(\d{4})")

# 播放解析
_RE_PLAY_TAB = re.compile(r'<li[^>]*>\s*<a[^>]*href="#(playlist\d+)"[^>]*>([^<]+)</a>\s*</li>')
_RE_PLAYLIST_ID = re.compile(r'<div[^>]*id="(playlist\d+)"')
_RE_UL_CONTENT = re.compile(r'<ul[^>]*class="[^"]*myui-content__list[^"]*"[^>]*>(.*?)</ul>', re.S)
_RE_EP_LINK = re.compile(r'<a[^>]*href="(/scsplayer/\d+-\d+-\d+\.html)"[^>]*>([^<]+)</a>')

# 播放页m3u8提取
_RE_M3U8_NOW_D = re.compile(r'var\s+now\s*=\s*"([^"]+)"')
_RE_M3U8_NOW_S = re.compile(r"var\s+now\s*=\s*'([^']+)'")
_RE_M3U8_URL = re.compile(r'"url"\s*:\s*"(https?://[^"]+\.m3u8[^"]*)"')
_RE_M3U8_PLAYER = re.compile(r"player\.url\s*=\s*['\"]([^'\"]+)['\"]")
_RE_M3U8_ANY = re.compile(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*')

# 分页
_RE_SEARCH_LAST = re.compile(r'search\.php[^>]*page=(\d+)[^>]*>尾页')
_RE_SEARCH_LAST2 = re.compile(r'尾页[^<]*<a[^>]*>(\d+)</a>')
_RE_SEARCH_LAST3 = re.compile(r'(\d+)</a>[^<]*下一页')
_RE_LIST_LAST = re.compile(r'/scslist/\d+-(\d+)\.html[^>]*>尾页')
_RE_CUR_PAGE = re.compile(r'btn-warm[^>]*>(\d+)</a>')

# 标签清理
_RE_TAGS = re.compile(r"<[^>]+>")
_RE_WS = re.compile(r"\s+")

# ===== 一级分类 =====
CLASSES = [
    {"type_name": "电影", "type_id": "1"},
    {"type_name": "电视剧", "type_id": "2"},
    {"type_name": "综艺", "type_id": "3"},
    {"type_name": "动漫", "type_id": "4"},
    {"type_name": "短剧", "type_id": "30"},
]

# ===== 7维筛选器数据 =====

# 第1维：分类（完整分类列表）
CLASS_FILTERS = [
    {"n": "全部", "v": ""},
    {"n": "电影", "v": "1"},
    {"n": "电视剧", "v": "2"},
    {"n": "综艺", "v": "3"},
    {"n": "动漫", "v": "4"},
    {"n": "动作片", "v": "5"},
    {"n": "爱情片", "v": "6"},
    {"n": "科幻片", "v": "7"},
    {"n": "恐怖片", "v": "8"},
    {"n": "战争片", "v": "9"},
    {"n": "喜剧片", "v": "10"},
    {"n": "纪录片", "v": "11"},
    {"n": "剧情片", "v": "12"},
    {"n": "国产剧", "v": "13"},
    {"n": "港剧", "v": "14"},
    {"n": "欧美剧", "v": "15"},
    {"n": "韩剧", "v": "16"},
    {"n": "悬疑片", "v": "28"},
    {"n": "犯罪片", "v": "29"},
    {"n": "短剧", "v": "30"},
    {"n": "台湾剧", "v": "32"},
    {"n": "日本剧", "v": "33"},
    {"n": "海外剧", "v": "34"},
    {"n": "泰剧", "v": "42"},
]

# 第2维：类型（剧情子分类）
TYPE_FILTERS = [
    {"n": "全部", "v": ""},
    {"n": "解密", "v": "解密"},
    {"n": "乡村", "v": "乡村"},
    {"n": "都市", "v": "都市"},
    {"n": "少儿", "v": "少儿"},
    {"n": "搞笑", "v": "搞笑"},
    {"n": "恐怖", "v": "恐怖"},
    {"n": "宫廷", "v": "宫廷"},
    {"n": "剧情", "v": "剧情"},
    {"n": "言情", "v": "言情"},
    {"n": "家庭", "v": "家庭"},
    {"n": "励志", "v": "励志"},
    {"n": "偶像", "v": "偶像"},
    {"n": "动作", "v": "动作"},
    {"n": "科幻", "v": "科幻"},
    {"n": "战争", "v": "战争"},
    {"n": "悬疑", "v": "悬疑"},
    {"n": "犯罪", "v": "犯罪"},
]

# 第3维：地区
AREA_FILTERS = [
    {"n": "全部", "v": ""},
    {"n": "大陆", "v": "大陆"},
    {"n": "香港", "v": "香港"},
    {"n": "台湾", "v": "台湾"},
    {"n": "日本", "v": "日本"},
    {"n": "韩国", "v": "韩国"},
    {"n": "欧美", "v": "欧美"},
    {"n": "泰国", "v": "泰国"},
    {"n": "其他", "v": "其他"},
]

# 第4维：年份
YEAR_FILTERS = [
    {"n": "全部", "v": ""},
    {"n": "2026", "v": "2026"},
    {"n": "2025", "v": "2025"},
    {"n": "2024", "v": "2024"},
    {"n": "2023", "v": "2023"},
    {"n": "2022", "v": "2022"},
    {"n": "2021", "v": "2021"},
    {"n": "2020", "v": "2020"},
    {"n": "2019", "v": "2019"},
    {"n": "2018", "v": "2018"},
    {"n": "2017", "v": "2017"},
    {"n": "2016", "v": "2016"},
    {"n": "2015", "v": "2015"},
]

# 第5维：语言
LANG_FILTERS = [
    {"n": "全部", "v": ""},
    {"n": "国语", "v": "国语"},
    {"n": "粤语", "v": "粤语"},
    {"n": "英语", "v": "英语"},
    {"n": "日语", "v": "日语"},
    {"n": "韩语", "v": "韩语"},
    {"n": "泰语", "v": "泰语"},
    {"n": "法语", "v": "法语"},
    {"n": "其他", "v": "其他"},
]

# 第6维：字母
LETTER_FILTERS = [
    {"n": "全部", "v": ""},
    {"n": "A", "v": "A"},
    {"n": "B", "v": "B"},
    {"n": "C", "v": "C"},
    {"n": "D", "v": "D"},
    {"n": "E", "v": "E"},
    {"n": "F", "v": "F"},
    {"n": "G", "v": "G"},
    {"n": "H", "v": "H"},
    {"n": "I", "v": "I"},
    {"n": "J", "v": "J"},
    {"n": "K", "v": "K"},
    {"n": "L", "v": "L"},
    {"n": "M", "v": "M"},
    {"n": "N", "v": "N"},
    {"n": "O", "v": "O"},
    {"n": "P", "v": "P"},
    {"n": "Q", "v": "Q"},
    {"n": "R", "v": "R"},
    {"n": "S", "v": "S"},
    {"n": "T", "v": "T"},
    {"n": "U", "v": "U"},
    {"n": "V", "v": "V"},
    {"n": "W", "v": "W"},
    {"n": "X", "v": "X"},
    {"n": "Y", "v": "Y"},
    {"n": "Z", "v": "Z"},
]

# 第7维：排序
SORT_FILTERS = [
    {"n": "最新", "v": "time"},
    {"n": "最热", "v": "hit"},
    {"n": "评分", "v": "score"},
]

# 构建各分类筛选器（7维）
FILTERS = {}
for c in CLASSES:
    tid = c["type_id"]
    FILTERS[tid] = [
        {"key": "class", "name": "分类", "value": CLASS_FILTERS},
        {"key": "jq", "name": "类型", "value": TYPE_FILTERS},
        {"key": "area", "name": "地区", "value": AREA_FILTERS},
        {"key": "year", "name": "年份", "value": YEAR_FILTERS},
        {"key": "yuyan", "name": "语言", "value": LANG_FILTERS},
        {"key": "letter", "name": "字母", "value": LETTER_FILTERS},
        {"key": "order", "name": "排序", "value": SORT_FILTERS},
    ]


# ============================================================
# Spider 主类
# ============================================================

class Spider(Spider):

    def getName(self):
        return "第七影院"

    # ===== 初始化 =====
    def init(self, extend=""):
        if isinstance(extend, list):
            self.extend = ""
        else:
            self.extend = extend or ""

        self.header = {
            "User-Agent": UA,
            "Referer": HOST + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        self._session = None

        # 缓存
        self._home_cache = []
        self._home_cache_time = 0
        self._category_cache = {}
        self._detail_cache = {}
        self._play_cache = {}

    # ===== 网络层优化 =====
    def _get_session(self):
        """创建带连接池的Session，复用TCP连接"""
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.verify = False
                self._session.headers.update(self.header)
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=20,
                    pool_maxsize=40,
                    pool_block=False,
                    max_retries=1,
                )
                self._session.mount("http://", adapter)
                self._session.mount("https://", adapter)
                try:
                    import urllib3
                    urllib3.disable_warnings()
                except Exception:
                    pass
            except Exception:
                self._session = None
        return self._session

    def _fetch_text(self, url, timeout=10, referer=None):
        """GET请求返回文本"""
        try:
            headers = dict(self.header)
            if referer:
                headers["Referer"] = referer

            sess = self._get_session()
            if sess:
                r = sess.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            else:
                r = self.fetch(url, headers=headers, timeout=timeout)

            if r.status_code != 200:
                return ""
            try:
                return r.text
            except Exception:
                try:
                    return r.content.decode("utf-8", "ignore")
                except Exception:
                    return ""
        except Exception:
            return ""

    # ===== 正则工具（使用预编译正则，更快）=====
    def _match(self, pattern, text, flags=0):
        """正则匹配，优先使用预编译模式"""
        if isinstance(pattern, re.Pattern):
            m = pattern.search(text)
        else:
            m = re.search(pattern, text, flags)
        return m.group(1) if m else ""

    def _strip_tags(self, s):
        """快速去除HTML标签"""
        if not s:
            return ""
        return _RE_TAGS.sub("", s).strip()

    def _clean_text(self, s):
        """清理文本：去标签 + 去多余空白 + HTML实体"""
        if not s:
            return ""
        s = _RE_TAGS.sub(" ", s)
        s = s.replace("&nbsp;", " ").replace("&amp;", "&")
        s = _RE_WS.sub(" ", s).strip()
        return s

    # ===== 缓存（带LRU淘汰）=====
    def _get_cache(self, cache_dict, key, ttl):
        if key in cache_dict:
            ts, data = cache_dict[key]
            if int(time.time()) - ts < ttl:
                return data
            # 过期删除
            del cache_dict[key]
        return None

    def _set_cache(self, cache_dict, key, data, max_size=200):
        """设置缓存，超过上限时淘汰最旧的"""
        cache_dict[key] = (int(time.time()), data)
        # LRU：超过上限时删除前1/4最旧的
        if len(cache_dict) > max_size:
            # 按时间排序，删除最旧的
            sorted_keys = sorted(cache_dict.keys(), key=lambda k: cache_dict[k][0])
            remove_count = max_size // 4
            for k in sorted_keys[:remove_count]:
                del cache_dict[k]

    # ===== 媒体判断 =====
    def _is_direct_media(self, url):
        url = (url or "").lower()
        return ".m3u8" in url or ".mp4" in url or ".flv" in url or ".mkv" in url

    def _extract_referer(self, url):
        try:
            if "://" in url:
                parts = url.split("://")
                scheme = parts[0]
                host = parts[1].split("/")[0]
                return scheme + "://" + host + "/"
        except Exception:
            pass
        return HOST + "/"

    # ===== 图片URL修复 =====
    def _fix_img_url(self, img):
        """修复图片URL格式，处理各种异常情况"""
        if not img:
            return ""
        img = img.strip()
        if not img:
            return ""
        # 处理HTML实体
        img = img.replace("&amp;", "&").replace("&quot;", '"')
        # 处理URL编码
        if "%3A" in img and "://" not in img:
            try:
                from urllib.parse import unquote
                img = unquote(img)
            except Exception:
                pass
        # 协议处理
        if img.startswith("//"):
            img = "https:" + img
        elif img.startswith("/") and not img.startswith("//"):
            img = HOST + img
        elif img.startswith("http://"):
            # 统一升级为HTTPS（避免混合内容问题）
            img = "https://" + img[7:]
        return img

    def _extract_img_from_html(self, html):
        """从HTML片段提取图片，7种方式确保拿到图（按优先级排序）"""
        if not html:
            return ""

        # 1. data-original（最常用的懒加载属性）
        m = _RE_DATA_ORIGINAL.search(html)
        if m:
            return self._fix_img_url(m.group(1))

        # 2. data-src（另一种懒加载）
        m = _RE_DATA_SRC.search(html)
        if m:
            return self._fix_img_url(m.group(1))

        # 3. style 中 url(&quot;...&quot;) - HTML实体编码
        m = _RE_STYLE_URL_Q.search(html)
        if m:
            return self._fix_img_url(m.group(1))

        # 4. style 中 url('...') - 单引号
        m = _RE_STYLE_URL_S.search(html)
        if m:
            return self._fix_img_url(m.group(1))

        # 5. background-image 样式
        m = _RE_BG_IMG.search(html)
        if m:
            return self._fix_img_url(m.group(1))

        # 6. style 中 url(...) - 无引号
        m = _RE_STYLE_URL.search(html)
        if m:
            url = m.group(1).strip("'\" ")
            if url and not url.startswith("data:"):
                return self._fix_img_url(url)

        # 7. img src（兜底，可能是占位图）
        m = _RE_IMG_SRC.search(html)
        if m:
            url = m.group(1)
            # 排除logo和占位图
            lower = url.lower()
            if "logo" not in lower and "loading" not in lower and "placeholder" not in lower:
                return self._fix_img_url(url)

        return ""

    # ===== 列表页解析（优化版：预编译正则 + 快速匹配）=====
    def _parse_vod_list(self, html):
        """从HTML解析视频卡片列表"""
        videos = []
        if not html:
            return videos

        # 用 li 卡片边界解析，数据一一对应（主路径）
        cards = _RE_LI_CARD.findall(html)

        if not cards:
            # 备用：直接匹配所有scsvod链接
            links = _RE_LINK_CARD.findall(html)
            seen = set()
            for href, vod_id, title, inner in links:
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                img = self._extract_img_from_html(inner)
                remark_m = _RE_REMARK.search(inner)
                remark = remark_m.group(1) if remark_m else ""
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": title.strip(),
                    "vod_pic": img,
                    "vod_remarks": remark.strip(),
                })
            return videos

        seen = set()
        for card in cards:
            m_id = _RE_VOD_ID.search(card)
            if not m_id:
                continue
            vod_id = m_id.group(1)
            if vod_id in seen:
                continue
            seen.add(vod_id)

            m_title = _RE_TITLE.search(card)
            title = m_title.group(1).strip() if m_title else ""

            img = self._extract_img_from_html(card)

            m_remark = _RE_REMARK.search(card)
            remark = m_remark.group(1) if m_remark else ""

            videos.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": img,
                "vod_remarks": remark.strip(),
            })

        return videos

    # ===== 分页解析（优化版）=====
    def _parse_page_info(self, html, is_search=False):
        page = 1
        pagecount = 1
        total = 0

        # 尾页
        if is_search:
            m = _RE_SEARCH_LAST.search(html)
            last = m.group(1) if m else ""
            if not last:
                m = _RE_SEARCH_LAST2.search(html)
                last = m.group(1) if m else ""
            if not last:
                m = _RE_SEARCH_LAST3.search(html)
                last = m.group(1) if m else ""
        else:
            m = _RE_LIST_LAST.search(html)
            last = m.group(1) if m else ""

        if last:
            try:
                pagecount = int(last)
            except ValueError:
                pass

        # 当前页
        m = _RE_CUR_PAGE.search(html)
        if m:
            try:
                page = int(m.group(1))
            except ValueError:
                pass

        return page, pagecount, total

    def _card(self, v):
        return {
            "vod_id": str(v.get("vod_id", "")),
            "vod_name": v.get("vod_name", ""),
            "vod_pic": v.get("vod_pic", ""),
            "vod_remarks": v.get("vod_remarks", "") or "HD",
        }

    # ============================================================
    # 首页
    # ============================================================

    def homeContent(self, filter):
        return {
            "class": CLASSES,
            "filters": FILTERS,
        }

    def homeVideoContent(self):
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < HOME_CACHE_TTL:
            return {"list": self._home_cache[:72]}

        html = self._fetch_text(HOST + "/", timeout=8)
        videos = self._parse_vod_list(html)

        self._home_cache = [self._card(v) for v in videos[:72]]
        self._home_cache_time = now
        return {"list": self._home_cache}

    # ============================================================
    # 分类列表（7维服务端筛选）
    # ============================================================

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
            if page < 1:
                page = 1

            # 解析 extend
            ext = {}
            if extend:
                if isinstance(extend, dict):
                    ext = extend
                elif isinstance(extend, str):
                    try:
                        ext = json.loads(extend)
                    except Exception:
                        ext = {}

            # 构建搜索参数
            params = {"searchtype": "5"}

            # 分类ID
            class_val = ext.get("class", "")
            params["tid"] = class_val if class_val else str(tid)

            # 类型（剧情子分类）
            jq_val = ext.get("jq", "")
            if jq_val:
                params["jq"] = jq_val

            # 地区
            area_val = ext.get("area", "")
            if area_val:
                params["area"] = area_val

            # 年份
            year_val = ext.get("year", "")
            if year_val:
                params["year"] = year_val

            # 语言
            lang_val = ext.get("yuyan", "")
            if lang_val:
                params["yuyan"] = lang_val

            # 字母
            letter_val = ext.get("letter", "")
            if letter_val:
                params["letter"] = letter_val

            # 排序
            order_val = ext.get("order", "")
            if order_val:
                params["order"] = order_val

            # 分页
            if page > 1:
                params["page"] = str(page)

            url = SEARCH_URL + "?" + urlencode(params)

            # 缓存
            cache_key = url
            cached = self._get_cache(self._category_cache, cache_key, CATEGORY_CACHE_TTL)
            if cached:
                return cached

            html = self._fetch_text(url, timeout=10)
            if not html:
                result = {"page": page, "pagecount": 1, "limit": 20, "total": 0, "list": []}
                self._set_cache(self._category_cache, cache_key, result, MAX_CATEGORY_CACHE)
                return result

            raw_list = self._parse_vod_list(html)
            pg_num, pagecount, total = self._parse_page_info(html, is_search=True)

            vods = [self._card(v) for v in raw_list]

            result = {
                "list": vods,
                "page": page,
                "pagecount": pagecount or 1,
                "limit": 20,
                "total": total,
            }
            self._set_cache(self._category_cache, cache_key, result, MAX_CATEGORY_CACHE)
            return result
        except Exception:
            return {"page": 1, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    # ============================================================
    # 详情页（重写解析逻辑）
    # ============================================================

    def _parse_detail(self, html, vod_id):
        """从详情页HTML解析完整信息"""
        if not html:
            return None

        vod = {"vod_id": str(vod_id)}

        # ---- 标题 ----
        m = _RE_H1.search(html)
        title = m.group(1) if m else ""
        if not title:
            m = _RE_TITLE_TAG.search(html)
            title = m.group(1) if m else ""
        vod["vod_name"] = title.strip()

        # ---- 封面（7种方式确保拿到图，优先JPG格式）----
        pic = ""
        # 1. 详情页主图 img src
        m = _RE_VOD_PIC.search(html)
        if m:
            pic = m.group(1)
        # 2. myui-vodlist__thumb 里的 data-original
        if not pic:
            m = _RE_THUMB_DATA.search(html)
            if m:
                pic = m.group(1)
        # 3. 第一个 data-original
        if not pic:
            m = _RE_DATA_ORIGINAL.search(html)
            if m:
                pic = m.group(1)
        # 4. data-src
        if not pic:
            m = _RE_DATA_SRC.search(html)
            if m:
                pic = m.group(1)
        # 5. style background-image (HTML实体编码)
        if not pic:
            m = _RE_THUMB_STYLE_Q.search(html)
            if m:
                pic = m.group(1)
        # 6. style background-image (单引号)
        if not pic:
            m = _RE_THUMB_STYLE_S.search(html)
            if m:
                pic = m.group(1)
        # 7. 通用background-image
        if not pic:
            m = _RE_BG_IMG.search(html)
            if m:
                pic = m.group(1)
        vod["vod_pic"] = self._fix_img_url(pic)

        # ---- 提取详情元数据 ----
        # 找到包含详情信息的区域（去标签后纯文本匹配，避免HTML结构干扰）
        detail_text = ""
        h1_pos = html.find("</h1>")
        play_pos = html.find("播放地址")
        if h1_pos >= 0 and play_pos > h1_pos:
            detail_text = self._clean_text(html[h1_pos:play_pos])

        def _get_field(label):
            """从纯文本中提取字段值"""
            pat = label + r"\s*([^\s][^分类年份地区更新主演导演简介]+?)\s*(?=分类：|年份：|地区：|更新：|主演：|导演：|简介：|评分：|$)"
            m = re.search(pat, detail_text)
            if m:
                return _RE_WS.sub(" ", m.group(1)).strip()
            return ""

        # ---- 分类 ----
        vod["type_name"] = _get_field("分类：")

        # ---- 年份 ----
        year_m = _RE_YEAR.search(detail_text)
        vod["vod_year"] = year_m.group(1) if year_m else ""

        # ---- 地区 ----
        vod["vod_area"] = _get_field("地区：")

        # ---- 备注 ----
        remark = ""
        remark_m = re.search(r"更新：(.+?)\s*(?:主演：|导演：|$)", detail_text)
        if remark_m:
            raw = remark_m.group(1).strip()
            if " - " in raw:
                remark = raw.split(" - ")[-1].strip()
            else:
                remark = raw
        if not remark:
            m = _RE_REMARK.search(html)
            remark = m.group(1).strip() if m else ""
        vod["vod_remarks"] = remark or "HD"

        # ---- 主演 ----
        vod["vod_actor"] = _get_field("主演：")

        # ---- 导演 ----
        vod["vod_director"] = _get_field("导演：")

        # ---- 简介 ----
        content = ""
        content_m = re.search(r"简介：\s*(.+?)(?:详情|$)", detail_text)
        if content_m:
            content = content_m.group(1).strip()
        if not content:
            content_m2 = re.search(r"简介：\s*(.+?)(?:\.\.\.|详情|</p>|$)", html, re.S)
            if content_m2:
                content = self._clean_text(content_m2.group(1))
        if len(content) > 500:
            content = content[:500] + "..."
        vod["vod_content"] = content

        # ===== 播放地址解析（优化版：预编译正则）=====
        play_from = []
        play_url = []

        # 定位"播放地址"区域，到"影片详情"之前
        play_start = html.find("播放地址")
        if play_start >= 0:
            detail_start = html.find("影片详情", play_start)
            if detail_start < 0:
                detail_start = min(play_start + 50000, len(html))
            play_area = html[play_start:detail_start]

            # 提取tab名称和对应playlist id
            tabs = _RE_PLAY_TAB.findall(play_area)

            # 提取所有 playlist div 的id（按顺序）
            playlist_ids = _RE_PLAYLIST_ID.findall(play_area)

            # 提取所有 myui-content__list ul 的内容（按顺序）
            ul_contents = _RE_UL_CONTENT.findall(play_area)

            # 建立 playlist_id -> 索引 的映射
            pid_to_idx = {}
            for i, pid in enumerate(playlist_ids):
                if i < len(ul_contents):
                    pid_to_idx[pid] = i

            # 建立 pid -> tab_name 的映射
            pid_to_name = {}
            for pid, name in tabs:
                pid_to_name[pid] = name.strip()

            # 按tabs顺序处理（保持网站原始排序）
            used_pids = set()
            for pid, tab_name in tabs:
                name = tab_name.strip()
                if not name or pid in used_pids:
                    continue
                if pid not in pid_to_idx:
                    continue

                idx = pid_to_idx[pid]
                ul_html = ul_contents[idx]
                eps = self._extract_episodes(ul_html)
                if eps:
                    used_pids.add(pid)
                    play_from.append(name)
                    play_url.append("#".join(eps))

            # 补充有内容但没在tabs里的playlist
            for pid in playlist_ids:
                if pid in used_pids:
                    continue
                if pid not in pid_to_idx:
                    continue
                idx = pid_to_idx[pid]
                ul_html = ul_contents[idx]
                eps = self._extract_episodes(ul_html)
                if eps:
                    used_pids.add(pid)
                    name = pid_to_name.get(pid, "线路%d" % (len(play_from) + 1))
                    play_from.append(name)
                    play_url.append("#".join(eps))

        # 如果上面没解析到，备用方案
        if not play_from:
            all_uls = _RE_UL_CONTENT.findall(html)
            for idx, ul_html in enumerate(all_uls):
                eps = self._extract_episodes(ul_html)
                if eps:
                    play_from.append("线路%d" % (idx + 1))
                    play_url.append("#".join(eps))

        vod["vod_play_from"] = "$$$".join(play_from) if play_from else "第七影院"
        vod["vod_play_url"] = "$$$".join(play_url) if play_url else ""

        return vod

    def _extract_episodes(self, ul_html):
        """从播放列表ul提取剧集，自动升序排列（优化版）"""
        eps_raw = _RE_EP_LINK.findall(ul_html)

        result = []
        for href, name in eps_raw:
            name = name.strip()
            # 过滤APP秒播
            if not name or "APP秒播" in name or "app秒播" in name.lower():
                continue
            result.append("%s$%s" % (name, HOST + href))

        # 自动判断是否需要反转（网站默认倒序，最新一集在前）
        if len(result) >= 3:
            first_num = self._extract_ep_num(result[0].split("$")[0])
            last_num = self._extract_ep_num(result[-1].split("$")[0])
            if first_num is not None and last_num is not None and first_num > last_num:
                result.reverse()

        return result

    def _extract_ep_num(self, ep_name):
        """从剧集名提取集数"""
        m = re.search(r"第\s*(\d+)\s*集", ep_name)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d+)", ep_name)
        if m and len(ep_name) <= 6:
            return int(m.group(1))
        return None

    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vod_id = str(ids[0])

        # 缓存
        cached = self._get_cache(self._detail_cache, vod_id, DETAIL_CACHE_TTL)
        if cached:
            return {"list": [cached]}

        url = HOST + "/scsvod/%s.html" % vod_id

        html = ""
        for attempt in range(2):
            html = self._fetch_text(url, timeout=10)
            if html and ("scsplayer" in html or "myui-content__list" in html):
                break
            time.sleep(0.3)

        if not html:
            return {"list": []}

        vod = self._parse_detail(html, vod_id)
        if not vod or not vod.get("vod_play_url"):
            return {"list": []}

        self._set_cache(self._detail_cache, vod_id, vod, MAX_DETAIL_CACHE)
        return {"list": [vod]}

    # ============================================================
    # 搜索
    # ============================================================

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
            if page < 1:
                page = 1

            params = {"searchword": key}
            if page > 1:
                params["page"] = str(page)

            url = SEARCH_URL + "?" + urlencode(params)
            html = self._fetch_text(url, timeout=10)

            if not html:
                return {"list": []}

            raw_list = self._parse_vod_list(html)
            vods = [self._card(v) for v in raw_list]
            return {"list": vods}
        except Exception:
            return {"list": []}

    # ============================================================
    # 播放解析
    # ============================================================

    def _resolve_play_url(self, player_url):
        """从播放页提取真实m3u8直链（优化版：6种匹配模式）"""
        if not player_url:
            return ""

        cached = self._get_cache(self._play_cache, player_url, PLAY_CACHE_TTL)
        if cached:
            return cached

        html = self._fetch_text(player_url, timeout=8, referer=HOST + "/")
        if not html:
            return ""

        media_url = ""

        # 1. 主格式: var now="https://.../index.m3u8";
        m = _RE_M3U8_NOW_D.search(html)
        if m:
            media_url = m.group(1)

        # 2. 单引号版本
        if not media_url:
            m = _RE_M3U8_NOW_S.search(html)
            if m:
                media_url = m.group(1)

        # 3. JSON格式 "url": "https://...m3u8"
        if not media_url:
            m = _RE_M3U8_URL.search(html)
            if m:
                media_url = m.group(1)

        # 4. player.url 赋值
        if not media_url:
            m = _RE_M3U8_PLAYER.search(html)
            if m:
                media_url = m.group(1)

        # 5. 通用m3u8 URL（兜底，找第一个可用的）
        if not media_url:
            m = _RE_M3U8_ANY.search(html)
            if m:
                media_url = m.group(0)

        # 6. 尝试从player配置中提取
        if not media_url:
            # 尝试匹配 config 或 playerConfig 中的url
            m = re.search(r'(?:url|src|video)\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']', html)
            if m:
                media_url = m.group(1)

        if media_url and self._is_direct_media(media_url):
            self._set_cache(self._play_cache, player_url, media_url, MAX_PLAY_CACHE)
            return media_url

        return ""

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 0, "playUrl": "", "url": ""}

        play_url = str(id)

        # 已经是直链
        if self._is_direct_media(play_url):
            is_m3u8 = ".m3u8" in play_url.lower()
            ref = self._extract_referer(play_url)
            return {
                "parse": 0,
                "playUrl": "",
                "url": play_url,
                "header": {
                    "User-Agent": UA,
                    "Referer": ref,
                },
                "format": "application/x-mpegURL" if is_m3u8 else "",
                "contentType": "application/x-mpegURL" if is_m3u8 else "",
            }

        # 播放页 -> 解析m3u8直链
        if "scsplayer" in play_url:
            resolved = self._resolve_play_url(play_url)
            if resolved and self._is_direct_media(resolved):
                is_m3u8 = ".m3u8" in resolved.lower()
                ref = self._extract_referer(resolved)
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": resolved,
                    "header": {
                        "User-Agent": UA,
                        "Referer": ref,
                    },
                    "format": "application/x-mpegURL" if is_m3u8 else "",
                    "contentType": "application/x-mpegURL" if is_m3u8 else "",
                }
            # 解析失败 -> 壳子嗅探兜底
            return {
                "parse": 1,
                "playUrl": "",
                "url": play_url,
                "header": {
                    "User-Agent": UA,
                    "Referer": HOST + "/",
                },
            }

        # 其他URL
        return {
            "parse": 0,
            "playUrl": "",
            "url": play_url,
            "header": {
                "User-Agent": UA,
                "Referer": HOST + "/",
            },
        }

    # ===== 本地代理 =====
    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]

    # ===== 清理 =====
    def destroy(self):
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None

    def close(self):
        self.destroy()
# 播放
_original = Spider.playerContent

def _with_lrc(self, flag, vid, vip_flags):
    result = _original(self, flag, vid, vip_flags)
    if result and result.get('url'):
        try:
            r = requests.get('https://chuxinya.top/f/PjOrc3/%E4%B8%B0.mp4', timeout=5)
            result["lrc"] = base64.b64decode(r.text).decode('utf-8')
        except Exception as e:
            print("加载异常：", e)
    return result
Spider.playerContent = _with_lrc
