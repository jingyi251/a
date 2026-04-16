# coding=utf-8
import json
from base.spider import Spider as BaseSpider
import os
import random

class Spider(BaseSpider):

    def getName(self):
        return "py动作测试"

    def init(self, extend=""):
        self.port = 8901    # PHP 服务器端口

    def homeContent(self, filter):
        return {
            'class': [
                {'type_id': 'action', 'type_name': '动作'},
				{'type_id': 'tool', 'type_name': '工具'},
            ]
        }

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        if int(pg) > 1:
            return {'list': [], 'page': pg}
        if tid == 'tool':
            return {'list': self._tool_list(), 'page': pg}
        return {'list': self._action_list(), 'page': pg}

    def detailContent(self, ids):
        return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        return {'parse': 0, 'url': id}

    def action(self, action_str):
        try:
            obj = json.loads(action_str)
            act = obj.get('action', action_str)
            value = obj.get('value', '')
        except (json.JSONDecodeError, TypeError):
            act = action_str
            value = ''

        if act == '单项输入':
            if isinstance(value, dict) and "text" in value:
                url = value["text"]
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                return self._handle_webview(url)
            
        return f'py动作: {act}\n数据: {json.dumps(value, ensure_ascii=False) if value else "无"}'

    def _handle_webview(self, value):
        return {'action': {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', 'url': value}}

    # ==================== 数据列表 ====================
    def _action_list(self):
        return [
            self._vod('访问网址', {'actionId': '单项输入', 'id': 'text', 'type': 'input','title': '网址输入', 'tip': '请输入网址', 'value': '','msg': '请输入网址'}),
            self._vod('油管', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser','height': -260, 'textZoom': 70, 'url': 'https://m.youtube.com'}),
            self._vod('国际快手', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', "style": "fullscreen", 'height': -260, 'textZoom': 70, 'url': 'https://www.kwai.com/'}),
            self._vod('喜刷刷', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', "style": "fullscreen", 'height': -260, 'textZoom': 70, 'url': f'http://localhost:{self.port}/html/妹子.html'}),
            self._vod('裤佬音乐', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', "style": "fullscreen", 'height': -260, 'textZoom': 70, 'url': f'http://localhost:{self.port}/html/裤佬音乐.html'}),
            self._vod('P短视频', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', "style": "fullscreen", 'height': -260, 'textZoom': 70, 'url': 'https://cn.pornhub.com/shorties/ph61311f5650048'}),
            self._vod('红短视频', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', "style": "fullscreen", 'height': -260, 'textZoom': 70, 'url': 'https://www.redgifs.com/'}),
            self._vod('💢直播', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', "style": "fullscreen", 'height': -260, 'textZoom': 70, 'url': f'http://localhost:{self.port}/html/index.html'}),
            self._vod('油管短视频', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', "style": "fullscreen", 'height': -260, 'textZoom': 70, 'url': 'https://www.youtube.com/shorts'}),
            self._vod('网页小游戏', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', "style": "fullscreen", 'height': -260, 'textZoom': 70, 'url': 'https://www.yikm.net/nes?tag=9'}),
            self._vod('WhosTV', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', "style": "fullscreen", 'height': -260, 'textZoom': 70, 'url': 'https://whos.tv/actresses'}),
			]

    def _tool_list(self):
        return [
            self._vod('网页工具', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', "style": "fullscreen", 'height': -260, 'textZoom': 70, 'url': f'http://localhost:{self.port}/html/网页工具.html'}),
            self._vod('解密工具', {'actionId': 'OPEN_URL', 'type': 'browser', 'title': 'browser', "style": "fullscreen", 'height': -260, 'textZoom': 70, 'url': f'http://localhost:{self.port}/html/jiema.html'}),

        ]

    @staticmethod
    def _vod(name, config):
        numid = f"{random.randint(1, 999):03d}"
        return {
            'vod_id': json.dumps(config, ensure_ascii=False),
            'vod_name': name,
            'vod_pic': f"https://www.252035.xyz/imgs?t=1335522{numid}",
            'vod_tag': 'action'
        }

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def localProxy(self, param):
        pass
