import sys
import re
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = 'Jable.TV'
        self.host = 'https://jable.tv'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': 'https://jable.tv/',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8'
        }

    def getName(self): 
        return self.name

    def init(self, extend=""): 
        pass

    def isVideoFormat(self, url): 
        return '.m3u8' in url or url.endswith('.mp4')

    def manualVideoCheck(self): 
        return False

    # ================= 首页分类 =================
    def homeContent(self, filter):
        return {
            'class': [
                {'type_id': 'hot', 'type_name': '近期熱門'},
                {'type_id': 'latest-updates', 'type_name': '最新更新'},
                {'type_id': 'categories/bdsm', 'type_name': '女奴调教'},
                {'type_id': 'categories/sex-only', 'type_name': '直接開啪'},
                {'type_id': 'categories/chinese-subtitle', 'type_name': '中文字幕'},
                {'type_id': 'categories/insult', 'type_name': '凌辱快感'},
                {'type_id': 'categories/uniform', 'type_name': '制服诱惑'},
                {'type_id': 'categories/roleplay', 'type_name': '角色劇情'},
                {'type_id': 'categories/private-cam', 'type_name': '盜攝偷拍'},
                {'type_id': 'categories/uncensored', 'type_name': '無碼解放'},
                {'type_id': 'categories/pov', 'type_name': '男友視角'},
                {'type_id': 'categories/groupsex', 'type_name': '多P群交'},
                {'type_id': 'categories/pantyhose', 'type_name': '絲襪美腿'},
                {'type_id': 'categories/lesbian', 'type_name': '女同歡愉'}
            ]
        }

    def homeVideoContent(self): 
        return self.categoryContent('latest-updates', '1', False, {})

    # ================= 列表解析 =================
    def parse_list(self, html):
        videos = []
        blocks = re.findall(
            r'<div class="col-[^>]+">.*?video-img-box.*?</h6>',
            html,
            re.S
        )

        for block in blocks:
            link = re.search(r'href="[^"]*?/videos/([^/]+)/"', block)
            title = re.search(r'class="title".*?><a[^>]*>([^<]+)</a>', block, re.S)
            img = re.search(r'data-src="([^"]+)"', block)
            if not img:
                img = re.search(r'src="([^"]+)"', block)
            dur = re.search(r'class="label">([^<]+)</span>', block)

            if not link or not title:
                continue

            pic = img.group(1) if img else ''
            if pic.startswith('//'):
                pic = 'https:' + pic
            elif pic.startswith('/'):
                pic = self.host + pic

            videos.append({
                'vod_id': link.group(1),
                'vod_name': title.group(1).strip(),
                'vod_pic': pic,
                'vod_remarks': dur.group(1).strip() if dur else '',
                'style': {'ratio': 1.5, 'type': 'rect'}
            })

        return videos

    # ================= 分类（路径分页 · 关键修复） =================
    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg)

            if pg == 1:
                url = f'{self.host}/{tid}/'
            else:
                url = f'{self.host}/{tid}/{pg}/'

            res = self.fetch(url, headers=self.headers)
            videos = self.parse_list(res.text)

            return {
                'list': videos,
                'page': pg,
                'pagecount': 999,
                'limit': 24,
                'total': 9999
            }
        except Exception as e:
            return {'list': []}

    # ================= 详情页 =================
    def detailContent(self, ids):
        try:
            vid = ids[0]
            url = f'{self.host}/videos/{vid}/'
            res = self.fetch(url, headers=self.headers)
            html = res.text

            play_url = ''
            m = re.search(r"var\s+hlsUrl\s*=\s*'([^']+)'", html)
            if m:
                play_url = m.group(1)
            else:
                m = re.search(r'(https?://[^"\']+\.m3u8[^"\']*)', html)
                if m:
                    play_url = m.group(1)

            title = re.search(r'property="og:title"\s+content="([^"]+)"', html)
            pic = re.search(r'property="og:image"\s+content="([^"]+)"', html)
            desc = re.search(r'name="description"\s+content="([^"]+)"', html)

            return {
                'list': [{
                    'vod_id': vid,
                    'vod_name': title.group(1).strip() if title else vid,
                    'vod_pic': pic.group(1) if pic else '',
                    'type_name': 'JableTV',
                    'vod_content': desc.group(1).strip() if desc else '',
                    'vod_play_from': 'Jable',
                    'vod_play_url': f'播放${play_url}'
                }]
            }
        except:
            return {'list': []}

    # ================= 搜索（Jable 搜索本身不支持分页） =================
    def searchContent(self, key, quick, pg="1"):
        try:
            url = f'{self.host}/search/{key}/'
            res = self.fetch(url, headers=self.headers)
            return {'list': self.parse_list(res.text)}
        except:
            return {'list': []}

    # ================= 播放 =================
    def playerContent(self, flag, id, vipFlags):
        return {
            'parse': 0,
            'url': id,
            'header': self.headers,
            'jx': '0'
        }

    def destroy(self): 
        pass