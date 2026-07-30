import re
import json
import requests
from base.spider import Spider

class Spider(Spider):
    
    def getName(self):
        return "苹果视频-十区"
    
    def init(self, extend=""):
        super().init(extend)
        self.site_url = "https://6181016.xyz"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36",
            "Referer": self.site_url,
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self.sess = requests.Session()
        self.page_size = 20
    
    def fetch(self, url, timeout=10):
        try:
            return self.sess.get(url, headers=self.headers, timeout=timeout, verify=False)
        except:
            return None
    
    def _dec(self, t):
        try: return "".join([chr(ord(c)^128) for c in t])
        except: return t
    
    def homeContent(self, filter):
        cate_list = [
            {"type_name": "一区", "type_id": "1"},
            {"type_name": "全部", "type_id": "66"},
            {"type_name": "日欧", "type_id": "63"},
            {"type_name": "动漫", "type_id": "64"},
            {"type_name": "无码", "type_id": "65"},
            {"type_name": "字幕", "type_id": "69"},
            {"type_name": "P站", "type_id": "70"},
            {"type_name": "厂牌", "type_id": "68"},
            {"type_name": "网黄", "type_id": "71"},
            {"type_name": "JK", "type_id": "67"},
            {"type_name": "国产", "type_id": "72"},
            {"type_name": "热门", "type_id": "73"}
        ]
        r = self.fetch(f"{self.site_url}/index.php/vod/type/id/66.html")
        lst = []
        if r and r.status_code == 200:
            items = re.findall(r'<a[^>]*class="[^"]*vodbox[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S)
            for vod_id, block in items:
                if not vod_id.startswith('http'):
                    vod_id = self.site_url + vod_id
                te = re.search(r'<p[^>]*class="km-script"[^>]*>([^<]+)</p>', block)
                vod_name = self._dec(te.group(1).strip()) if te else "未知"
                pic = re.search(r'data-original=["\']([^"\']+)["\']', block)
                vod_pic = pic.group(1) if pic else ""
                if vod_pic.startswith('//'): vod_pic = 'https:' + vod_pic
                lst.append({"vod_id": vod_id, "vod_name": vod_name, "vod_pic": vod_pic})
        return {"class": cate_list, "list": lst}
    
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        url = f"{self.site_url}/index.php/vod/type/id/{tid}.html"
        if pg > 1:
            url = f"{self.site_url}/index.php/vod/type/id/{tid}/page/{pg}.html"
        
        res = self.fetch(url)
        video_list = []
        seen_ids = set()
        
        if res and res.status_code == 200:
            html = res.text
            items = re.findall(r'<a[^>]*class="[^"]*vodbox[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S)
            
            for href, block in items:
                vod_id = href
                if not vod_id.startswith('http'):
                    vod_id = self.site_url + vod_id
                if vod_id in seen_ids: continue
                seen_ids.add(vod_id)
                
                te = re.search(r'<p[^>]*class="km-script"[^>]*>([^<]+)</p>', block)
                vod_name = self._dec(te.group(1).strip()) if te else "未知"
                
                pic = re.search(r'data-original=["\']([^"\']+)["\']', block)
                vod_pic = pic.group(1) if pic else ""
                if vod_pic.startswith('//'): vod_pic = 'https:' + vod_pic
                
                video_list.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": ""
                })
        
        pagecount = pg + 1
        m = re.search(r'totalPages\s*=\s*[\"\'](\d+)[\"\']', res.text) if res and res.status_code == 200 else None
        if m:
            tp = int(m.group(1))
            pagecount = (tp + 30) // 16 + 5
        
        return {
            "list": video_list,
            "page": pg,
            "pagecount": pagecount,
            "limit": self.page_size,
            "total": 9999
        }
    
    def detailContent(self, ids):
        vod_id = ids[0] if ids else ""
        if not vod_id:
            return {"list": []}
        
        # 提取标题
        vod_name = "视频"
        scsc_match = re.search(r'/html/(?:scsc|acac)/([^\.]+)', vod_id)
        if scsc_match:
            pp = scsc_match.group(1)
            if pp: vod_name = self._dec(pp)
        
        # 直接返回原始播放页链接，让playerContent处理
        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": "",
                "vod_play_from": "默认",
                "vod_play_url": f"1${vod_id}"
            }]
        }
    
    def playerContent(self, flag, id, vipFlags):
        if "$" in id:
            play_url = id.split("$")[1]
        else:
            play_url = id
        
        # 从播放页URL提取v参数
        qs_match = re.search(r'\?v=([^&]+)', play_url)
        if qs_match:
            from urllib.parse import unquote
            m3u8_url = unquote(qs_match.group(1))
            m3u8_url = m3u8_url.replace('d2wexzpo1hxhi0', 'd2m0k739byzwun')
            token = ('?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
                     'eyJ0aW1lc3RhbXAiOjE3ODE3MDg0MDQzNjUzMDM2MDAsInR5cGUiOjAsInVpZCI6NTUzNDcxNDN9.'
                     'LiIcl5qe1yhUX6fj5iCke9-S-ULHxxGK5hibHY_qcxc&c=https://zzzsts.lkkwip.cn')
            return {"parse": 0, "url": m3u8_url + token}
        
        if re.search(r'\.(m3u8|mp4|flv)(\?|$)', play_url, re.I):
            return {"parse": 0, "url": play_url}
        return {"parse": 1, "url": play_url}
    
    def searchContent(self, key, quick, pg=1):
        pg = int(pg) if str(pg).isdigit() else 1
        search_url = f"{self.site_url}/index.php/vod/search/page/{pg}/wd/{requests.utils.quote(key)}.html"
        res = self.fetch(search_url)
        video_list = []
        seen_ids = set()
        if res and res.status_code == 200:
            items = re.findall(r'<a[^>]*class="[^"]*vodbox[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', res.text, re.S)
            for vod_id, block in items:
                if not vod_id.startswith('http'):
                    vod_id = self.site_url + vod_id
                if vod_id in seen_ids: continue
                seen_ids.add(vod_id)
                te = re.search(r'<p[^>]*class="km-script"[^>]*>([^<]+)</p>', block)
                vod_name = self._dec(te.group(1).strip()) if te else "未知"
                pic = re.search(r'data-original=["\']([^"\']+)["\']', block)
                vod_pic = pic.group(1) if pic else ""
                if vod_pic.startswith('//'): vod_pic = 'https:' + vod_pic
                video_list.append({"vod_id": vod_id, "vod_name": vod_name, "vod_pic": vod_pic})
        pagecount = pg + 1 if len(video_list) else pg
        return {"list": video_list, "page": pg, "pagecount": pagecount, "limit": self.page_size, "total": len(video_list)}