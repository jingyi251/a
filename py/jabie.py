# coding=utf-8
"""
目标站: Jable.TV  适配 TVBox (Py 引擎)
修复：强化 m3u8 播放链接提取，避免直接 fallback 到页面解析
"""
import re
import sys
import urllib.parse
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        self.site_url = "https://jable.tv"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        }

    def homeContent(self, filter):
        url = self.site_url + "/"
        resp = self.fetch(url, headers=self.headers)
        categories = []
        if resp:
            soup = BeautifulSoup(resp.text, 'html.parser')
            nav_links = soup.select('nav.app-nav a')
            for a in nav_links:
                href = a.get('href', '').strip()
                name = a.get_text(strip=True)
                if not href or 'javascript' in href or name == '':
                    continue
                if href.startswith(self.site_url) or href.startswith('/'):
                    path = href if href.startswith('/') else href.replace(self.site_url, '')
                    path = path.strip('/')
                    # 过滤掉外链广告（如 /c1/...）
                    if path.startswith('c') and len(path) > 2 and path[1].isdigit():
                        continue
                    categories.append({"type_id": path, "type_name": name})
        seen = set()
        unique_cat = []
        for c in categories:
            if c['type_id'] not in seen:
                seen.add(c['type_id'])
                unique_cat.append(c)
        video_list = self._parse_video_list(resp) if resp else []
        return {"class": unique_cat, "list": video_list[:20], "filters": {}}

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        base = f"{self.site_url}/{tid}/"
        params = {}
        if page > 1:
            params['page'] = page
        if extend:
            for k, v in extend.items():
                if v:
                    params[k] = v
        query = urllib.parse.urlencode(params)
        url = base if not query else f"{base}?{query}"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = self._parse_video_list(resp)
        pagecount = 1
        pager = soup.select('.pagination a')
        if pager:
            nums = []
            for a in pager:
                t = a.get_text(strip=True)
                if t.isdigit():
                    nums.append(int(t))
            if nums:
                pagecount = max(nums)
            else:
                if any('下一頁' in a.get_text() for a in pager):
                    pagecount = page + 1
        if len(video_list) < 24:
            pagecount = page
        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": len(video_list) * pagecount
        }

    def _parse_video_list(self, resp):
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        cards = soup.select('.video-img-box')
        if not cards:
            cards = soup.select('#site-content .container .row .col .row .video-img-box')
        for card in cards:
            img_box_a = card.select_one('div.img-box > a')
            if not img_box_a:
                continue
            href = img_box_a.get('href', '')
            match = re.search(r'/videos/([^/]+)', href)
            if not match:
                continue
            vod_id = match.group(1)
            title_elem = card.select_one('div.detail h6.title')
            vod_name = title_elem.get_text(strip=True) if title_elem else '未知标题'
            img_elem = img_box_a.select_one('img.lazyload')
            vod_pic = ''
            if img_elem:
                vod_pic = img_elem.get('data-src') or img_elem.get('src') or ''
            video_list.append({
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_remarks": ''
            })
        return video_list

    # ---------- 详情页（重点修复播放链接提取） ----------
    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/videos/{vod_id}/"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": []}

        soup = BeautifulSoup(resp.text, 'html.parser')
        vod_name = ''
        name_elem = soup.select_one('h1.title') or soup.select_one('h4') or soup.select_one('.video-title')
        if name_elem:
            vod_name = name_elem.get_text(strip=True)

        vod_pic = ''
        img_elem = soup.select_one('div.video-thumbnail img') or soup.select_one('img.lazyload')
        if img_elem:
            vod_pic = img_elem.get('data-src') or img_elem.get('src') or ''

        vod_content = ''
        desc_elem = soup.select_one('.description') or soup.select_one('meta[name="description"]')
        if desc_elem:
            if desc_elem.name == 'meta':
                vod_content = desc_elem.get('content', '')
            else:
                vod_content = desc_elem.get_text(strip=True)

        actor_elems = soup.select('a[href*="/models/"]')
        actors = [a.get_text(strip=True) for a in actor_elems if a.get_text(strip=True)]
        vod_actor = ', '.join(actors) if actors else ''
        director_elem = soup.select_one('a[href*="/director/"]')
        vod_director = director_elem.get_text(strip=True) if director_elem else ''

        # ===== 增强的 m3u8 提取逻辑 =====
        m3u8_link = self._extract_m3u8(resp.text, soup)

        vod_play_from = '高清'
        vod_play_url = ''
        if m3u8_link:
            vod_play_url = f'高清${m3u8_link}'
        else:
            # 极小概率仍获取不到，此时保留页面解析能力
            vod_play_url = f'解析${url}'

        result = [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]
        return {"list": result}

    # 提取 m3u8 的辅助函数
    def _extract_m3u8(self, html_text, soup):
        """从页面 HTML/JS 中挖掘 .m3u8 链接"""
        candidates = set()
        # 1. 从所有 script 标签内容中搜索
        script_texts = []
        for script in soup.select('script'):
            if script.string:
                script_texts.append(script.string)
        full_js = '\n'.join(script_texts)

        # 2. 使用多种常见变量赋值模式匹配
        patterns = [
            r'(?:videoSource|source|src|file|hlsUrl|url)\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)',
            r'["\']([^"\']+\.m3u8)["\']',  # 宽泛捕获所有 .m3u8 字符串
        ]
        for pat in patterns:
            for m in re.finditer(pat, full_js, re.IGNORECASE):
                link = m.group(1)
                # 过滤明显不是视频的链接（如第三方统计）
                if any(s in link.lower() for s in ['google', 'facebook', 'analytics', 'pixel']):
                    continue
                candidates.add(link)

        # 3. 如果 script 中没找到，再从原始 html 中搜索（有些写在 data 属性里）
        if not candidates:
            for m in re.finditer(r'["\']([^"\']+\.m3u8)["\']', html_text, re.IGNORECASE):
                link = m.group(1)
                if any(s in link.lower() for s in ['google', 'facebook', 'analytics', 'pixel']):
                    continue
                candidates.add(link)

        # 4. 补全链接并返回第一个有效项
        for link in candidates:
            if link.startswith('//'):
                link = 'https:' + link
            elif link.startswith('/'):
                link = self.site_url + link
            # 简单合法性检查
            if link.startswith('http') and '.m3u8' in link:
                return link
        return None

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}/search/?keyword={encoded_key}"
        if page > 1:
            url += f"&page={page}"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}
        video_list = self._parse_video_list(resp)
        return {
            "list": video_list,
            "page": page,
            "pagecount": 1,
            "limit": 24,
            "total": len(video_list)
        }

    # ---------- 播放器处理 ----------
    def playerContent(self, flag, id, vipFlags):
        # 若传入的 id 已经是完整的 m3u8 链接，则直接播放，无需再解析
        if id.startswith('http') and '.m3u8' in id:
            return {"parse": 0, "url": id, "header": self.headers}
        # 否则尝试当做页面地址进行解析
        return {"parse": 1, "url": id, "header": self.headers}