# -*- coding: utf-8 -*-
"""
合并插件：央视频（直播）+ YouTube 台湾新闻直播 + 外部直连/解析频道
- 频道配置统一为 TXT（M3U风格），支持远程URL或直接传入内容
- 路由：fun=cctv（直连直播） 或 fun=yttv（代理） 或 fun=external（外部频道）
- YouTube 代理可用性在每次生成列表时动态检测
- 日志默认关闭，通过 log_enabled 开启
- 央视频缓存机制与 live_ysp.py 完全一致（磁盘+内存，含重试）
- 支持混合配置：内置频道、直连频道、解析接口 JSON 共存于一个 TXT
"""

import re
import sys
import os
import time
import json
import base64
import struct
import binascii
import hashlib
import random
import threading
from datetime import datetime
from urllib.parse import quote, unquote, urljoin, urlparse, urlunparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def getProxyUrl(self):
            return "http://127.0.0.1:9978/proxy?do=py&"
        def init(self, extend): pass
        def getName(self): return "Live"
        def liveContent(self, url): return ""
        def localProxy(self, params): return []
        def destroy(self): return ""

# ========================= 默认频道配置（完整列表 + 扩展示例） =========================
DEFAULT_TXT = """央视直播,#genre#
CCTV1,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv1&cnlid=2024078201&livepid=600001859&defn=fhd
CCTV2,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv2&cnlid=2024075401&livepid=600001800&defn=fhd
CCTV3,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv3&cnlid=2024068501&livepid=600001801&defn=fhd
CCTV4,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv4&cnlid=2029797101&livepid=600001814&defn=fhd
CCTV5,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv5&cnlid=2024078401&livepid=600001818&defn=fhd
CCTV5+,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv5p&cnlid=2024078001&livepid=600001817&defn=fhd
CCTV6,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv6&cnlid=2013693901&livepid=600108442&defn=fhd
CCTV7,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv7&cnlid=2024072001&livepid=600004092&defn=fhd
CCTV8,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv8&cnlid=2029793001&livepid=600001803&defn=fhd
CCTV9,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv9&cnlid=2024078601&livepid=600004078&defn=fhd
CCTV10,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv10&cnlid=2024078701&livepid=600001805&defn=fhd
CCTV11,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv11&cnlid=2027248701&livepid=600001806&defn=fhd
CCTV12,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv12&cnlid=2027248801&livepid=600001807&defn=fhd
CCTV13,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv13&cnlid=2029797201&livepid=600001811&defn=fhd
CCTV14,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv14&cnlid=2027248901&livepid=600001809&defn=fhd
CCTV15,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv15&cnlid=2027249001&livepid=600001815&defn=fhd
CCTV16,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv16&cnlid=2027249101&livepid=600098637&defn=fhd
CCTV16(4K),http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv164k&cnlid=2027249301&livepid=600099502&defn=fhd
CCTV17,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv17&cnlid=2027249401&livepid=600001810&defn=fhd
CCTV4K,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv4k&cnlid=2029810301&livepid=600002264&defn=fhd
CCTV8K,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctv8k&cnlid=2026774101&livepid=600156816&defn=fhd

卫视直播,#genre#
北京卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=bjws&cnlid=2024052703&livepid=600002309&defn=fhd
江苏卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=jsws&cnlid=2024171103&livepid=600002521&defn=fhd
东方卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=dfws&cnlid=2024054503&livepid=600002483&defn=fhd
浙江卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=zjws&cnlid=2024054703&livepid=600002520&defn=fhd
湖南卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=hnws&cnlid=2024054803&livepid=600002475&defn=fhd
湖北卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=hbws&cnlid=2024171203&livepid=600002508&defn=fhd
广东卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=gdws&cnlid=2024060903&livepid=600002485&defn=fhd
广西卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=gxws&cnlid=2024060703&livepid=600002509&defn=fhd
黑龙江卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=hljws&cnlid=2029797003&livepid=600002498&defn=fhd
海南卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=hnws2&cnlid=2024055603&livepid=600002506&defn=fhd
重庆卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cqws&cnlid=2024061103&livepid=600002531&defn=fhd
深圳卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=szws&cnlid=2024061303&livepid=600002481&defn=fhd
四川卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=scws&cnlid=2024061403&livepid=600002516&defn=fhd
河南卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=henanws&cnlid=2029797303&livepid=600002525&defn=fhd
东南卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=fjdnhz&cnlid=2024061503&livepid=600002484&defn=fhd
贵州卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=gzhws&cnlid=2024061603&livepid=600002490&defn=fhd
江西卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=jxws&cnlid=2024061703&livepid=600002503&defn=fhd
辽宁卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=lnws&cnlid=2024171303&livepid=600002505&defn=fhd
安徽卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=ahws&cnlid=2024171403&livepid=600002532&defn=fhd
河北卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=hbws2&cnlid=2024171503&livepid=600002493&defn=fhd
山东卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=sdws&cnlid=2029787903&livepid=600002513&defn=fhd
天津卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=tjws&cnlid=2019927003&livepid=600152137&defn=fhd
吉林卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=jlws&cnlid=2025561503&livepid=600190405&defn=fhd
陕西卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=shanxiws&cnlid=2029795103&livepid=600190400&defn=fhd
宁夏卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=nxws&cnlid=2025608503&livepid=600190737&defn=fhd
内蒙古卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=nmgws&cnlid=2025561203&livepid=600190401&defn=fhd
云南卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=ynws&cnlid=2025561303&livepid=600190402&defn=fhd
山西卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=shanxiws2&cnlid=2025560803&livepid=600190407&defn=fhd
青海卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=qhws&cnlid=2025559103&livepid=600190406&defn=fhd
西藏卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=xzws&cnlid=2025558003&livepid=600190403&defn=fhd
新疆卫视,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=xjws&cnlid=2019927403&livepid=600152138&defn=fhd
中国教育电视台1,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cetv1&cnlid=2022823801&livepid=600171827&defn=fhd

数字付费,#genre#
风云剧场,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvfyjc&cnlid=2025637103&livepid=600099658&defn=shd
第一剧场,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvdyjc&cnlid=2026874203&livepid=600099655&defn=shd
怀旧剧场,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvhjjc&cnlid=2026874303&livepid=600099620&defn=shd
世界地理,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvsjdl&cnlid=2026874403&livepid=600099637&defn=shd
风云音乐,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvfyyy&cnlid=2026874503&livepid=600099660&defn=shd
兵器科技,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvbqkj&cnlid=2026874603&livepid=600099649&defn=shd
风云足球,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvfyzq&cnlid=2026966203&livepid=600099636&defn=shd
高尔夫·网球,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvgeqwq&cnlid=2026874703&livepid=600099659&defn=shd
女性时尚,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvnxss&cnlid=2026874803&livepid=600099650&defn=shd
央视文化精品,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvyswhjp&cnlid=2026874903&livepid=600099653&defn=shd
央视台球,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvystq&cnlid=2026875003&livepid=600099652&defn=shd
电视指南,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvdszn&cnlid=2026875103&livepid=600099656&defn=shd
卫生健康,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cctvwsjk&cnlid=2025637003&livepid=600099651&defn=shd
国学频道,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=gxpd&cnlid=2029360403&livepid=600213139&defn=shd

海外直播,#genre#
CGTN,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cgtn&cnlid=2024181701&livepid=600014550&defn=fhd
CGTN法语频道,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cgtnfy&cnlid=2024181801&livepid=600084704&defn=fhd
CGTN俄语频道,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cgtney&cnlid=2024181901&livepid=600084758&defn=fhd
CGTN阿拉伯语频道,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cgtnalby&cnlid=2024182001&livepid=600084782&defn=fhd
CGTN西班牙语频道,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cgtnxby&cnlid=2024182101&livepid=600084744&defn=fhd
CGTN外语纪录频道,http://127.0.0.1:9978/proxy?do=py&fun=cctv&id=cgtnwyjl&cnlid=2024182301&livepid=600084781&defn=fhd

港台直播,#genre#
中天新聞,https://www.youtube.com/@中天電視CtiTv/streams/1
TVBS新聞,https://www.youtube.com/@TVBSNEWS01/streams/1
東森新聞,https://www.youtube.com/@newsebc/streams/1
民視新聞,https://www.youtube.com/@FTV_News/streams/1

IPTV央视|直连,#genre#,header={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36","uid":"123456"},"proxy": "proxy"
CCTV-1 综合,http://home.hfr1107.top:14520/rtp/239.49.8.19:9614
CCTV-2 财经,http://home.hfr1107.top:14520/rtp/239.49.8.50:9802

IPTV卫视|直连,#genre#,header={"User-Agent": "Goiptv/8.8.8","uid":"514752"},"proxy": "noproxy"
江苏卫视4K-50FPS,http://home.hfr1107.top:14520/rtp/239.49.1.62:8000
江苏卫视,http://home.hfr1107.top:14520/rtp/239.49.8.16:9602

接口|解析,#genre#
[
    {
      "name": "👖裤佬IPTV直播",
      "type": 0,
      "proxy": "noproxy",
      "url": "https://live.445569.xyz/live.m3u"
    },
    {
      "name": "☀️┃日后TV┃M3U",
      "type": 0,
      "url": "http://rihou.cc:555/gggg.nzk",
      "playerType": 2,
      "ua": "okhttp/3",
      "epg": "https://epg.112114.eu.org/?ch={name}&date={date}",
      "logo": "https://epg.112114.eu.org/logo/{name}.png"
    },
    {
      "name": "👨┃JackTV┃M3U",
      "url": "https://php.946985.filegear-sg.me/jackTV.m3u",
      "proxy": "proxy",
      "header": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
      }
    }
]
"""
# ========================= 央视频 CKey 管理器（完整版） =========================
class CKeyManager:
    DELTA = 0x9e3779b9
    ROUNDS = 16
    LOG_ROUNDS = 4
    SALT_LEN = 2
    ZERO_LEN = 7
    TEA_CKEY = binascii.unhexlify('59b2f7cf725ef43c34fdd7c123411ed3')
    GUARD_TEA_KEY = binascii.unhexlify('110DBEC10C23E7D2E56A1CAD6914EF1B')

    def __init__(self):
        self.xorKey = bytes([0x84, 0x2E, 0xED, 0x08, 0xF0, 0x66, 0xE6, 0xEA,
                             0x48, 0xB4, 0xCA, 0xA9, 0x91, 0xED, 0x6F, 0xF3])
        self.guardXorKey = bytes([0xB3, 0xC9, 0x53, 0xA0, 0x69, 0x13, 0xAD, 0x4D])
        self.standardAlphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
        self.customAlphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-='
        self.guid = ''
        self.generate_guid()

    def generate_guid(self):
        parts = [
            format(random.getrandbits(32), '08x'),
            format(random.getrandbits(16), '04x'),
            format(random.getrandbits(16), '04x'),
            format(random.getrandbits(16), '04x'),
            format(random.getrandbits(48), '012x')
        ]
        self.guid = ''.join(parts)
        if len(self.guid) != 32:
            self.guid = self.guid.ljust(32, '0')
        return self.guid

    @staticmethod
    def calc_signature(buffer_bytes):
        signature = 0
        for b in buffer_bytes:
            signature = (0x83 * signature + b) & 0x7FFFFFFF
        return signature

    def custom_decode(self, text):
        if not text:
            return b''
        text = text.rstrip('=')
        if len(text) % 4 != 0:
            text += '=' * (4 - len(text) % 4)
        trans = str.maketrans(self.customAlphabet[:64], self.standardAlphabet[:64])
        translated = text.translate(trans)
        return base64.b64decode(translated)

    def custom_encode(self, data):
        encoded = base64.b64encode(data).decode()
        trans = str.maketrans(self.standardAlphabet[:64], self.customAlphabet[:64])
        translated = encoded.translate(trans)
        return translated.rstrip('=')

    def xor_array(self, byte_array):
        if isinstance(byte_array, bytes):
            byte_array = list(byte_array)
        result = bytearray(len(byte_array))
        for i, b in enumerate(byte_array):
            result[i] = b ^ self.xorKey[i & 0xF]
        return bytes(result)

    def tea_encrypt_ecb(self, p_in_buf, p_key):
        if len(p_in_buf) < 8:
            p_in_buf = p_in_buf.ljust(8, b'\0')
        y, z = struct.unpack('>2I', p_in_buf[:8])
        k = struct.unpack('>4I', p_key[:16])
        sum_val = 0
        for _ in range(self.ROUNDS):
            sum_val = (sum_val + self.DELTA) & 0xFFFFFFFF
            y = (y + (((z << 4) + k[0]) ^ (z + sum_val) ^ ((z >> 5) + k[1]))) & 0xFFFFFFFF
            z = (z + (((y << 4) + k[2]) ^ (y + sum_val) ^ ((y >> 5) + k[3]))) & 0xFFFFFFFF
        return struct.pack('>2I', y, z)

    def tea_decrypt_ecb(self, p_in_buf, p_key):
        y, z = struct.unpack('>2I', p_in_buf[:8])
        k = struct.unpack('>4I', p_key[:16])
        sum_val = (self.DELTA << self.LOG_ROUNDS) & 0xFFFFFFFF
        for _ in range(self.ROUNDS):
            z = (z - (((y << 4) + k[2]) ^ (y + sum_val) ^ ((y >> 5) + k[3]))) & 0xFFFFFFFF
            y = (y - (((z << 4) + k[0]) ^ (z + sum_val) ^ ((z >> 5) + k[1]))) & 0xFFFFFFFF
            sum_val = (sum_val - self.DELTA) & 0xFFFFFFFF
        return struct.pack('>2I', y, z)

    def oi_symmetry_encrypt2(self, p_in_buf, n_in_buf_len, p_key):
        n_pad_salt_body_zero_len = n_in_buf_len + 1 + self.SALT_LEN + self.ZERO_LEN
        n_pad_len = n_pad_salt_body_zero_len % 8
        if n_pad_len:
            n_pad_len = 8 - n_pad_len

        p_out_buf = bytearray()
        src_buf = bytearray(8)
        src_buf[0] = (random.randint(0, 255) & 0xF8) | n_pad_len
        src_i = 1

        while n_pad_len:
            src_buf[src_i] = random.randint(0, 255)
            src_i += 1
            n_pad_len -= 1

        iv_plain = bytearray(8)
        iv_crypt = bytearray(8)

        i = 0
        while i < self.SALT_LEN:
            if src_i < 8:
                src_buf[src_i] = random.randint(0, 255)
                src_i += 1
                i += 1
            if src_i == 8:
                for j in range(8):
                    src_buf[j] ^= iv_crypt[j]
                temp_out = self.tea_encrypt_ecb(bytes(src_buf), p_key)
                temp_bytes = list(temp_out)
                for j in range(8):
                    temp_bytes[j] ^= iv_plain[j]
                iv_plain = src_buf[:]
                iv_crypt = bytes(temp_bytes)
                p_out_buf.extend(temp_bytes)
                src_i = 0

        p_in_buf_index = 0
        while n_in_buf_len:
            if src_i < 8:
                src_buf[src_i] = p_in_buf[p_in_buf_index]
                p_in_buf_index += 1
                src_i += 1
                n_in_buf_len -= 1
            if src_i == 8:
                for j in range(8):
                    src_buf[j] ^= iv_crypt[j]
                temp_out = self.tea_encrypt_ecb(bytes(src_buf), p_key)
                temp_bytes = list(temp_out)
                for j in range(8):
                    temp_bytes[j] ^= iv_plain[j]
                iv_plain = src_buf[:]
                iv_crypt = bytes(temp_bytes)
                p_out_buf.extend(temp_bytes)
                src_i = 0

        i = 0
        while i < self.ZERO_LEN:
            if src_i < 8:
                src_buf[src_i] = 0
                src_i += 1
                i += 1
            if src_i == 8:
                for j in range(8):
                    src_buf[j] ^= iv_crypt[j]
                temp_out = self.tea_encrypt_ecb(bytes(src_buf), p_key)
                temp_bytes = list(temp_out)
                for j in range(8):
                    temp_bytes[j] ^= iv_plain[j]
                iv_plain = src_buf[:]
                iv_crypt = bytes(temp_bytes)
                p_out_buf.extend(temp_bytes)
                src_i = 0

        if src_i > 0:
            for j in range(src_i, 8):
                src_buf[j] = 0
            for j in range(8):
                src_buf[j] ^= iv_crypt[j]
            temp_out = self.tea_encrypt_ecb(bytes(src_buf), p_key)
            temp_bytes = list(temp_out)
            for j in range(8):
                temp_bytes[j] ^= iv_plain[j]
            p_out_buf.extend(temp_bytes)

        return bytes(p_out_buf)

    def oi_symmetry_decrypt2(self, p_in_buf, n_in_buf_len, p_key):
        if n_in_buf_len % 8 != 0 or n_in_buf_len < 16:
            return None
        dest_buf = list(self.tea_decrypt_ecb(p_in_buf[:8], p_key))
        n_pad_len = dest_buf[0] & 0x07
        i = n_in_buf_len - 1
        i = i - n_pad_len - self.SALT_LEN - self.ZERO_LEN
        if i < 0:
            return None
        p_out_buf_len = i

        iv_pre_crypt = bytearray(8)
        iv_cur_crypt = list(p_in_buf[:8])
        p_in_buf_offset = 8
        dest_i = 1 + n_pad_len

        salt_count = 1
        while salt_count <= self.SALT_LEN:
            if dest_i < 8:
                dest_i += 1
                salt_count += 1
            elif dest_i == 8:
                iv_pre_crypt = iv_cur_crypt[:]
                iv_cur_crypt = list(p_in_buf[p_in_buf_offset:p_in_buf_offset+8])
                for j in range(8):
                    if p_in_buf_offset + j >= n_in_buf_len:
                        return None
                    dest_buf[j] ^= iv_cur_crypt[j]
                temp_buf = self.tea_decrypt_ecb(bytes(dest_buf), p_key)
                dest_buf = list(temp_buf)
                p_in_buf_offset += 8
                dest_i = 0

        plain_bytes = bytearray()
        n_plain_len = p_out_buf_len
        while n_plain_len > 0:
            if dest_i < 8:
                plain_bytes.append(dest_buf[dest_i] ^ iv_pre_crypt[dest_i])
                dest_i += 1
                n_plain_len -= 1
            elif dest_i == 8:
                iv_pre_crypt = iv_cur_crypt[:]
                iv_cur_crypt = list(p_in_buf[p_in_buf_offset:p_in_buf_offset+8])
                for j in range(8):
                    if p_in_buf_offset + j >= n_in_buf_len:
                        return None
                    dest_buf[j] ^= iv_cur_crypt[j]
                temp_buf = self.tea_decrypt_ecb(bytes(dest_buf), p_key)
                dest_buf = list(temp_buf)
                p_in_buf_offset += 8
                dest_i = 0
        return bytes(plain_bytes)

    def generate_ck_guard_time(self, timestamp, guid, guard_data='-1', package_name='null', process_name='null'):
        body = struct.pack('>I', timestamp)
        for part in [self.guard_last_five(guid), self.guard_last_five(package_name),
                     self.guard_last_five(process_name), guard_data]:
            body += struct.pack('>H', len(part)) + part.encode('utf-8')
        plain = struct.pack('>H', len(body)) + body
        checksum = self.calc_signature(plain)
        encrypted = self.oi_symmetry_encrypt2(plain, len(plain), self.GUARD_TEA_KEY)
        encrypted += struct.pack('>I', checksum)
        bytes_list = list(encrypted)
        for i in range(len(bytes_list)):
            bytes_list[i] ^= self.guardXorKey[i & 7]
        return binascii.hexlify(bytes(bytes_list)).decode().upper()

    @staticmethod
    def guard_last_five(value):
        s = str(value)
        return s[-5:] if len(s) >= 5 else ''

    def encrypt_data_to_ckey(self, data):
        data_len = len(data)
        checksum = self.calc_signature(data)
        encrypted = self.oi_symmetry_encrypt2(data, data_len, self.TEA_CKEY)
        encrypted += struct.pack('>I', checksum)
        xor_encrypted = self.xor_array(encrypted)
        base64_encoded = self.custom_encode(xor_encrypted)
        return "--01" + base64_encoded

    def decrypt_ckey_to_data(self, ckey):
        ckey_without_prefix = ckey[4:]
        base64_decoded = self.custom_decode(ckey_without_prefix)
        if base64_decoded is None:
            return None
        xor_decrypted = self.xor_array(base64_decoded)
        data_len = len(xor_decrypted) - 4
        encrypted_data = xor_decrypted[:data_len]
        checksum_bytes = xor_decrypted[data_len:]
        checksum = struct.unpack('>I', checksum_bytes)[0]
        decrypted = self.oi_symmetry_decrypt2(encrypted_data, data_len, self.TEA_CKEY)
        if decrypted is None:
            return None
        return {'data': decrypted, 'checksum': checksum}

    def build_packet(self, params):
        data = bytearray(binascii.unhexlify('0000004200000004000004d2'))
        data += struct.pack('>I', params['Platform'])
        data += struct.pack('>I', 0)
        data += struct.pack('>I', params['Timestamp'])
        for key in ['Sdtfrom', 'randFlag', 'appVer', 'vid', 'guid']:
            val = params[key].encode('utf-8')
            data += struct.pack('>H', len(val)) + val
        data += struct.pack('>I', 1)
        data += struct.pack('>I', 1)
        uid = "2622783A".encode('utf-8')
        data += struct.pack('>H', len(uid)) + uid
        bundleID = "nil".encode('utf-8')
        data += struct.pack('>H', len(bundleID)) + bundleID
        uuid4 = params['uuid4'].encode('utf-8')
        data += struct.pack('>H', len(uuid4)) + uuid4
        data += struct.pack('>H', len(bundleID)) + bundleID
        ckeyVersion = "v0.1.000".encode('utf-8')
        data += struct.pack('>H', len(ckeyVersion)) + ckeyVersion
        packageName = "com.cctv.yangshipin.app.iphone".encode('utf-8')
        data += struct.pack('>H', len(packageName)) + packageName
        platform_str = "4330403".encode('utf-8')
        data += struct.pack('>H', len(platform_str)) + platform_str
        ex_json_bus = "ex_json_bus".encode('utf-8')
        data += struct.pack('>H', len(ex_json_bus)) + ex_json_bus
        ex_json_vs = "ex_json_vs".encode('utf-8')
        data += struct.pack('>H', len(ex_json_vs)) + ex_json_vs
        ck_guard_time = params['ck_guard_time'].encode('utf-8')
        data += struct.pack('>H', len(ck_guard_time)) + ck_guard_time

        body_length = len(data)
        buffer = struct.pack('>H', body_length) + data
        signature = self.calc_signature(buffer)
        buffer = buffer[:18] + struct.pack('>I', signature) + buffer[22:]
        return buffer

    def generate_ckey(self, cnlid, timestamp=None):
        if timestamp is None:
            timestamp = int(time.time())
        randFlag = base64.b64encode(os.urandom(18)).decode()
        uuid4 = f"{random.getrandbits(16):04x}{random.getrandbits(16):04x}-{random.getrandbits(16):04x}-{random.getrandbits(16):04x}-{random.getrandbits(16):04x}-{random.getrandbits(16):04x}{random.getrandbits(16):04x}{random.getrandbits(16):04x}"
        ck_guard_time = self.generate_ck_guard_time(timestamp, self.guid)
        params = {
            'Platform': 4330403,
            'Timestamp': timestamp,
            'Sdtfrom': 'dcgh',
            'vid': cnlid,
            'guid': self.guid,
            'appVer': 'V8.22.1035.3031',
            'randFlag': randFlag,
            'uuid4': uuid4,
            'ck_guard_time': ck_guard_time
        }
        buffer = self.build_packet(params)
        ckey = self.encrypt_data_to_ckey(buffer)
        return {'ckey': ckey, 'params': params}

    def make_live_request(self, cnlid, livepid, defn):
        self.generate_guid()
        ckey_result = self.generate_ckey(cnlid)
        ckey = ckey_result['ckey']
        params = ckey_result['params']

        flowid = f"{random.getrandbits(16):04X}{random.getrandbits(16):04X}-{random.getrandbits(16):04X}-{random.getrandbits(16):04X}-{random.getrandbits(16):04X}-{random.getrandbits(16):04X}{random.getrandbits(16):04X}{random.getrandbits(16):04X}_4330403"

        spvcode = "MSgzMDoyMTYwLDYwOjIxNjB8MzA6MjE2MCw2MDoyMTYwKTsyKDMwOjIxNjAsNjA6MjE2MHwzMDoyMTYwLDYwOjIxNjAp"

        request_params = {
            "atime": "120",
            "livepid": livepid,
            "cnlid": cnlid,
            "appVer": "V8.22.1035.3031",
            "app_version": "300090",
            "caplv": "1",
            "cmd": "2",
            "defn": defn,
            "device": "iPhone",
            "encryptVer": "4.2",
            "getpreviewinfo": "0",
            "hevclv": "33",
            "lang": "zh-Hans_JP",
            "livequeue": "0",
            "logintype": "1",
            "nettype": "1",
            "newnettype": "1",
            "newplatform": "4330403",
            "platform": "4330403",
            "sdtfrom": "v3021",
            "spacode": "23",
            "spaudio": "1",
            "spdemuxer": "6",
            "spdrm": "2",
            "spdynamicrange": "7",
            "spflv": "1",
            "spflvaudio": "1",
            "sphdrfps": "60",
            "sphttps": "0",
            "spvcode": spvcode,
            "spvideo": "4",
            "stream": "1",
            "system": "1",
            "sysver": "ios18.2.1",
            "uhd_flag": "4",
            "cKey": ckey,
            "guid": self.guid,
            "fntick": str(params['Timestamp']),
            "flowid": flowid,
            "playbacktime": "0"
        }
        return self.send_http_request(request_params)

    def send_http_request(self, params):
        url = "https://bkliveinfo.ysp.cctv.cn"
        headers = {
            'User-Agent': 'qqlive',
            'Connection': 'Keep-Alive',
            'Accept': 'application/json'
        }
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('iretcode') == 0:
                    playurl = data.get('playurl')
                    return {'success': True, 'playurl': playurl}
                else:
                    return {'success': False, 'iretcode': data.get('iretcode')}
            else:
                return {'success': False, 'http_code': resp.status_code}
        except Exception:
            return {'success': False, 'error': 'request failed'}

    def get_play_url(self, cnlid, livepid, defn):
        result = self.make_live_request(cnlid, livepid, defn)
        if result.get('success') and result.get('playurl'):
            return result['playurl']
        return None
# ========================= YouTube 直播提取器 =========================
class YouTubeLiveLite:
    def __init__(self, session, headers=None, config=None):
        self.session = session
        self.headers = headers or {}
        self.config = config or {}
        self.cache = {}
        self.cache_ttl = int(self.config.get('live_cache_ttl') or 45)

    @staticmethod
    def extract_video_id(text):
        text = str(text or '').strip()
        for pattern in [
            r'(?:v=|/v/|/embed/|/shorts/|youtu\.be/)([0-9A-Za-z_-]{11})',
            r'^([0-9A-Za-z_-]{11})$',
        ]:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        raise Exception('无法识别 YouTube 视频 ID')

    def extract_live(self, url_or_id):
        video_id = self.extract_video_id(url_or_id)
        now = time.time()
        cached = self.cache.get(video_id)
        if cached and cached.get('expires', 0) > now:
            return cached.get('data')

        watch_url = f'https://www.youtube.com/watch?v={video_id}'
        response = self._get(watch_url)
        page = response.text
        player_response = self._extract_initial_player_response(page) or {}
        ytcfg = self._extract_ytcfg(page) or {}
        api_key = ytcfg.get('INNERTUBE_API_KEY') or self._search(r'"INNERTUBE_API_KEY":"([^"]+)"', page)
        visitor_data = self._extract_visitor_data(ytcfg, player_response)
        status_obj = player_response.get('playabilityStatus') or {}
        streaming = player_response.get('streamingData') or {}
        details = player_response.get('videoDetails') or {}

        page_hls_url = streaming.get('hlsManifestUrl') or ''
        api_data = None
        if api_key:
            api_data = self._call_player_api(video_id, api_key, ytcfg, watch_url, visitor_data)
            if api_data:
                api_streaming = api_data.get('streamingData') or {}
                api_details = api_data.get('videoDetails') or {}
                api_hls_url = api_streaming.get('hlsManifestUrl') or ''
                if api_hls_url:
                    streaming = api_streaming
                elif not page_hls_url and api_streaming:
                    streaming = api_streaming
                if api_details:
                    details = api_details
                status_obj = api_data.get('playabilityStatus') or status_obj
        if not (streaming.get('hlsManifestUrl') or '') and page_hls_url:
            streaming = dict(streaming or {})
            streaming['hlsManifestUrl'] = page_hls_url

        hls_url = streaming.get('hlsManifestUrl') or ''
        is_live = bool(details.get('isLiveContent') or hls_url)
        status = status_obj.get('status') or ''
        reason = status_obj.get('reason') or ''
        title = details.get('title') or video_id

        data = {
            'id': video_id,
            'title': title,
            'is_live': is_live,
            'status': status,
            'reason': reason,
            'hls_url': hls_url,
            'duration': int(details.get('lengthSeconds') or 0),
        }
        self.cache[video_id] = {'data': data, 'expires': time.time() + self.cache_ttl}
        return data

    def _get(self, url, **kwargs):
        headers = self.headers.copy()
        headers.update(kwargs.pop('headers', {}) or {})
        response = self.session.get(url, headers=headers, timeout=kwargs.pop('timeout', 30), **kwargs)
        response.raise_for_status()
        return response

    def _post_json(self, url, payload, headers=None):
        final_headers = self.headers.copy()
        final_headers.update({'Content-Type': 'application/json', 'Origin': 'https://www.youtube.com'})
        if headers:
            final_headers.update({k: v for k, v in headers.items() if v})
        response = self.session.post(url, json=payload, headers=final_headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def _call_player_api(self, video_id, api_key, ytcfg, referer, visitor_data=None):
        context = ytcfg.get('INNERTUBE_CONTEXT') or {
            'client': {'clientName': 'WEB', 'clientVersion': '2.20240310.01.00', 'hl': 'en', 'gl': 'US'}
        }
        clients = [
            {'client': {'clientName': 'ANDROID', 'clientVersion': '21.02.35', 'androidSdkVersion': 30, 'userAgent': 'com.google.android.youtube/21.02.35 (Linux; U; Android 11) gzip', 'osName': 'Android', 'osVersion': '11', 'hl': 'en', 'gl': 'US'}},
            {'client': {'clientName': 'IOS', 'clientVersion': '21.02.3', 'deviceMake': 'Apple', 'deviceModel': 'iPhone16,2', 'userAgent': 'com.google.ios.youtube/21.02.3 (iPhone16,2; U; CPU iOS 18_3_2 like Mac OS X;)', 'osName': 'iPhone', 'osVersion': '18.3.2.22D82', 'hl': 'en', 'gl': 'US'}},
            {'client': {'clientName': 'MWEB', 'clientVersion': '2.20260115.01.00', 'userAgent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1', 'hl': 'en', 'gl': 'US'}},
            context,
        ]
        for ctx in clients:
            client = ctx.get('client') or {}
            client_name = client.get('clientName') or 'WEB'
            try:
                url = f'https://www.youtube.com/youtubei/v1/player?key={quote(api_key)}&prettyPrint=false'
                headers = {
                    'Referer': referer,
                    'X-YouTube-Client-Name': str(self._client_name_id(client_name)),
                    'X-YouTube-Client-Version': client.get('clientVersion') or '',
                }
                if visitor_data:
                    headers['X-Goog-Visitor-Id'] = visitor_data
                if client.get('userAgent'):
                    headers['User-Agent'] = client.get('userAgent')
                payload = {
                    'context': ctx,
                    'videoId': video_id,
                    'contentCheckOk': True,
                    'racyCheckOk': True,
                }
                data = self._post_json(url, payload, headers=headers)
                streaming = data.get('streamingData') or {}
                if streaming.get('hlsManifestUrl'):
                    data['_client_name'] = client_name
                    return data
            except Exception:
                continue
        return None

    def _extract_visitor_data(self, ytcfg, player_response):
        return (
            self.config.get('visitor_data')
            or ytcfg.get('VISITOR_DATA')
            or (((ytcfg.get('INNERTUBE_CONTEXT') or {}).get('client') or {}).get('visitorData'))
            or ((player_response.get('responseContext') or {}).get('visitorData'))
        )

    def _extract_ytcfg(self, text):
        match = re.search(r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;', text or '', re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except Exception:
            return None

    def _extract_initial_player_response(self, text):
        return self._extract_json_after(text, 'ytInitialPlayerResponse')

    def _extract_json_after(self, text, marker):
        pos = (text or '').find(marker)
        if pos < 0:
            return None
        start = text.find('{', pos)
        if start < 0:
            return None
        depth = 0
        in_str = None
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if in_str:
                if char == in_str:
                    in_str = None
                continue
            if char in ('"', "'"):
                in_str = char
                continue
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:index + 1])
                    except Exception:
                        return None
        return None

    @staticmethod
    def _search(pattern, text, default=None):
        match = re.search(pattern, text or '', re.S)
        return match.group(1) if match else default

    def _client_name_id(self, client_name):
        return {
            'WEB': 1,
            'MWEB': 2,
            'ANDROID': 3,
            'IOS': 5,
            'TVHTML5': 7,
            'ANDROID_VR': 28,
            'WEB_EMBEDDED_PLAYER': 56,
            'WEB_REMIX': 67,
        }.get(client_name, 1)


# ========================= 外部频道管理器（修正版） =========================
class ExternalChannelManager:
    """管理直连和解析频道，提供按来源分类编号"""
    def __init__(self):
        self.channels = []          # 所有外部频道列表
        self.id_map = {}            # id -> channel dict
        self.next_id = 1
        # 按来源存储分类顺序
        self.source_groups = {}     # source -> [group1, group2, ...]
        self.source_order = []      # 记录 source 出现顺序
        self.group_number_map = {}  # (source, group) -> number

    def add_channel(self, name, group, url, headers=None, proxy=False, source='direct'):
        if headers is None:
            headers = {}
        ch = {
            'name': name,
            'group': group,
            'url': url,
            'headers': headers,
            'proxy': proxy,
            'source': source,
            'id': f"ext_{self.next_id}"
        }
        self.next_id += 1
        self.channels.append(ch)
        self.id_map[ch['id']] = ch

        # 记录来源和分类顺序
        if source not in self.source_groups:
            self.source_groups[source] = []
            self.source_order.append(source)
        if group not in self.source_groups[source]:
            self.source_groups[source].append(group)
        return ch

    def assign_group_numbers(self):
        """按来源顺序分配全局递增编号"""
        number = 1
        for source in self.source_order:
            for group in self.source_groups[source]:
                self.group_number_map[(source, group)] = number
                number += 1

    def get_group_number(self, source, group):
        return self.group_number_map.get((source, group), 0)

    def get_channel_by_id(self, ch_id):
        return self.id_map.get(ch_id)


# ========================= 合并后的 Spider 类（完整版，含编码修正） =========================
class Spider(BaseSpider):
    # 全局变量（模拟原 live_ysp.py 的模块级变量）
    CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, 0o755, True)

    _lock_dict = {}
    _lock_dict_lock = threading.Lock()
    _fail_count_dict = {}
    _fail_count_lock = threading.Lock()

    CACHE_TTL = 300
    M3U8_CONTENT_CACHE_TTL = 5
    EXTERNAL_CACHE_TTL = 300  # 外部接口内容缓存时间

    def __init__(self):
        super().__init__()
        self.log_enabled = False
        self.log_file = '/sdcard/Download/live_plugin.log'
        self.ytb_enabled = False
        self.session_ytb = None
        self.session_ysp = None
        self.channels = []          # 内置频道（YSP+YTB）列表，供 liveContent 输出
        self.ytb_url_map = {}       # 内置 YTB 频道映射
        self.yt = None
        # YSP 内存缓存（m3u8）
        self._m3u8_cache = {}
        self._m3u8_cache_lock = threading.Lock()
        # YTB 缓存
        self.video_cache = {}
        self.m3u8_cache = {}
        self.fail_cache = {}
        # 外部频道管理
        self.ext_manager = ExternalChannelManager()
        # 外部接口内容缓存
        self._ext_cache = {}
        self._ext_cache_lock = threading.Lock()
        # 解析接口名称映射
        self._parse_names = []

    def _log(self, msg, data=None):
        if not self.log_enabled:
            return
        try:
            line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
            if data is not None:
                if isinstance(data, (dict, list)):
                    line += ' ' + json.dumps(data, ensure_ascii=False, default=str)
                else:
                    line += ' ' + str(data)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except Exception:
            pass

    def init(self, extend):
        try:
            extend_dict = json.loads(extend) if extend else {}
        except:
            extend_dict = {}

        self.log_enabled = extend_dict.get('log_enabled', False)
        # 读取 ext 中传递的代理列表
        self.ext_proxies = extend_dict.get('proxy', [])
        if self.ext_proxies:
            self._log("从ext读取到代理列表", {"proxies": self.ext_proxies})
        self._log("Spider init", extend_dict)

        # ---- 1. 创建两个 Session ----
        # YSP: 直连，强制不使用代理
        self.session_ysp = requests.Session()
        self.session_ysp.proxies = {'http': None, 'https': None}
        adapter = HTTPAdapter(
            pool_connections=3, pool_maxsize=5,
            max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        )
        self.session_ysp.mount("http://", adapter)
        self.session_ysp.mount("https://", adapter)
        self.session_ysp.headers.update({
            'User-Agent': 'qqlive',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        })

        # YTB: 需代理，先空创建，后续探测
        self.session_ytb = requests.Session()
        retry_ytb = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        adapter_ytb = HTTPAdapter(max_retries=retry_ytb, pool_connections=5, pool_maxsize=10)
        self.session_ytb.mount('http://', adapter_ytb)
        self.session_ytb.mount('https://', adapter_ytb)
        self.session_ytb.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.youtube.com/'
        })

        # ---- 2. 获取原始配置文本（来自远程或 extend） ----
        raw_txt = None
        if 'channels_url' in extend_dict:
            url = extend_dict['channels_url']
            try:
                resp = self.session_ysp.get(url, timeout=10)
                if resp.status_code == 200:
                    resp.encoding = 'utf-8'   # 强制 UTF-8 解码，避免乱码
                    raw_txt = resp.text
                    self._log("从远程加载配置", {"url": url})
                else:
                    self._log("远程加载失败", {"url": url, "status": resp.status_code})
            except Exception as e:
                self._log("远程加载异常", {"url": url, "error": repr(e)})
        elif 'channels' in extend_dict:
            raw_txt = extend_dict['channels']
            self._log("从extend直接读取配置")
        else:
            raw_txt = DEFAULT_TXT
            self._log("使用默认配置")

        # ---- 3. 拆分配置 ----
        builtin_txt, direct_txt, parse_list = self._parse_full_config(raw_txt)

        # ---- 4. 加载内置频道 ----
        if builtin_txt:
            self._load_channels(builtin_txt)
        else:
            # 如果拆分为空，尝试使用原逻辑（兼容旧配置）
            self._load_channels(raw_txt)

        # 初始化 YouTube 提取器（在加载内置频道之后）
        self.yt = YouTubeLiveLite(self.session_ytb, self.session_ytb.headers, {})

        # ---- 5. 加载直连频道 ----
        if direct_txt:
            self._log("加载直连频道配置")
            self._parse_direct_channels(direct_txt)

        # ---- 6. 加载解析接口 ----
        if parse_list:
            self._log("加载解析接口", {"count": len(parse_list)})
            for idx, item in enumerate(parse_list):
                self._parse_remote_interface(item, idx)

        # ---- 7. 为外部频道分配分类编号 ----
        self.ext_manager.assign_group_numbers()

        # ---- 8. 代理检测 ----
        self._check_ytb_available()

        self._log("初始化完成", {
            "ytb_enabled": self.ytb_enabled,
            "内置频道数": len(self.channels),
            "外部频道数": len(self.ext_manager.channels)
        })

    # ==================== 配置拆分（支持混合配置） ====================
    def _parse_full_config(self, raw_text):
        """
        将混合配置拆分为内置频道、直连频道、解析接口。
        返回 (builtin_txt, direct_txt, parse_list)
        """
        lines = raw_text.splitlines()
        builtin_lines = []
        direct_lines = []
        parse_json = None
        in_direct_section = False
        in_parse_section = False
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # 检测分类行
            if '#genre#' in line:
                parts = line.split(',')
                group = parts[0].strip()
                if group.startswith('#'):
                    group = group[1:].strip()
                # 判断是否为直连分类（含“直连”或“|直连”）
                if '直连' in group or group.endswith('直连'):
                    in_direct_section = True
                    in_parse_section = False
                    direct_lines.append(line)   # 保留分类行
                    i += 1
                    continue
                # 判断是否为解析分类（“接口|解析”或“解析”）
                if '解析' in group or group.startswith('接口'):
                    in_parse_section = True
                    in_direct_section = False
                    # 下一行应该是 JSON 数组，开始收集
                    i += 1
                    # 跳过空行
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    # 收集 JSON 直到遇到 ']' 且括号平衡
                    json_start = i
                    brace_count = 0
                    bracket_count = 0
                    in_string = False
                    escape = False
                    for j in range(i, len(lines)):
                        chunk = lines[j]
                        for ch in chunk:
                            if escape:
                                escape = False
                                continue
                            if ch == '\\':
                                escape = True
                                continue
                            if ch == '"' and not escape:
                                in_string = not in_string
                                continue
                            if not in_string:
                                if ch == '{':
                                    brace_count += 1
                                elif ch == '}':
                                    brace_count -= 1
                                elif ch == '[':
                                    bracket_count += 1
                                elif ch == ']':
                                    bracket_count -= 1
                        if brace_count == 0 and bracket_count == 0 and ']' in chunk and j > i:
                            json_end = j + 1
                            break
                    else:
                        # 未找到结束，放弃
                        parse_json = None
                        break
                    json_text = '\n'.join(lines[i:json_end])
                    try:
                        parse_json = json.loads(json_text)
                        if not isinstance(parse_json, list):
                            parse_json = [parse_json]
                    except:
                        parse_json = None
                    i = json_end
                    continue
            
            # 普通行
            if in_direct_section:
                direct_lines.append(line)
            elif in_parse_section:
                # 解析部分已经处理完 JSON，之后的行忽略
                pass
            else:
                builtin_lines.append(line)
            i += 1
        
        builtin_txt = '\n'.join(builtin_lines)
        direct_txt = '\n'.join(direct_lines)
        parse_list = parse_json if isinstance(parse_json, list) else []
        return builtin_txt, direct_txt, parse_list

    def _clean_group(self, group):
        """去除分类名中的 |直连、|解析 等来源标识，只保留核心名称"""
        if not group:
            return '默认分类'
        # 如果包含 |直连 或 |解析，取 | 前的部分
        if '|直连' in group or '|解析' in group:
            return group.split('|')[0].strip()
        # 也处理可能出现的其他后缀
        for suffix in ['直连', '解析']:
            if group.endswith(suffix):
                return group[:-len(suffix)].strip()
        return group.strip()

    # ==================== 内置频道加载（保持不变） ====================
    def _load_channels(self, raw_text):
        self.channels = []
        self.ytb_url_map = {}
        lines = raw_text.splitlines()
        current_group = "未知分组"
        ytb_counter = 1

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '#genre#' in line:
                parts = line.split(',')
                if parts:
                    group = parts[0].strip()
                    if group.startswith('#'):
                        group = group[1:].strip()
                    if group:
                        current_group = group
                continue
            if ',' in line:
                name_part, url_part = line.split(',', 1)
                name = name_part.strip()
                url = url_part.strip()
                if not name or not url:
                    continue

                if ('youtube.com' in url or 'youtu.be' in url) and '127.0.0.1' not in url:
                    vid = f"ytb_{ytb_counter}"
                    ytb_counter += 1
                    self.ytb_url_map[vid] = url
                    proxy_url = f"http://127.0.0.1:9978/proxy?do=py&fun=yttv&id={vid}"
                    self.channels.append({
                        'name': name,
                        'group': current_group,
                        'proxy_url': proxy_url,
                        'is_ytb': True,
                        'id': vid,
                        'source': 'builtin_ytb'
                    })
                else:
                    self.channels.append({
                        'name': name,
                        'group': current_group,
                        'proxy_url': url,
                        'is_ytb': False,
                        'id': None,
                        'source': 'builtin_ysp'
                    })
        self._log("内置频道加载完成", {"total": len(self.channels), "ytb": len(self.ytb_url_map)})

    # ==================== 外部直连频道解析 ====================
    def _parse_direct_channels(self, text):
        """解析直连 TXT，支持分类行和频道行附加 header/proxy"""
        lines = text.splitlines()
        current_group = "默认分类"
        default_headers = {}
        default_proxy = False

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '#genre#' in line:
                parts = line.split(',')
                group_name = parts[0].strip()
                if group_name.startswith('#'):
                    group_name = group_name[1:].strip()
                # 清洗分类名
                group_name = self._clean_group(group_name)
                extra = ','.join(parts[1:]) if len(parts) > 1 else ''
                headers = {}
                proxy = False
                header_match = re.search(r'header\s*=\s*({.+?})(?:,|$)', extra, re.IGNORECASE)
                if header_match:
                    try:
                        headers = json.loads(header_match.group(1))
                    except:
                        pass
                proxy_match = re.search(r'proxy\s*=\s*["\']?(\w+)["\']?', extra, re.IGNORECASE)
                if proxy_match and proxy_match.group(1).lower() == 'proxy':
                    proxy = True
                current_group = group_name
                default_headers = headers
                default_proxy = proxy
                continue

            if ',' not in line:
                continue
            parts = line.split(',')
            name = parts[0].strip()
            url = parts[1].strip() if len(parts) > 1 else ''
            if not name or not url:
                continue

            headers = default_headers.copy()
            proxy = default_proxy
            if len(parts) > 2:
                extra = ','.join(parts[2:])
                header_match = re.search(r'header\s*=\s*({.+?})(?:,|$)', extra, re.IGNORECASE)
                if header_match:
                    try:
                        headers.update(json.loads(header_match.group(1)))
                    except:
                        pass
                proxy_match = re.search(r'proxy\s*=\s*["\']?(\w+)["\']?', extra, re.IGNORECASE)
                if proxy_match:
                    proxy = (proxy_match.group(1).lower() == 'proxy')

            self.ext_manager.add_channel(
                name=name,
                group=current_group,
                url=url,
                headers=headers,
                proxy=proxy,
                source='direct'
            )

    # ==================== 解析接口（远程）处理 ====================
    def _parse_remote_interface(self, item, idx):
        name = item.get('name', f'接口{idx+1}')
        url = item.get('url')
        if not url:
            self._log(f"解析接口 {name} 缺少 url，跳过")
            return
        self._parse_names.append(name)

        headers = {}
        if 'header' in item and isinstance(item['header'], dict):
            headers.update(item['header'])
        if 'ua' in item:
            headers['User-Agent'] = item['ua']
        if 'Referer' in item:
            headers['Referer'] = item['Referer']
        exclude_keys = {'name', 'url', 'type', 'proxy', 'playerType', 'epg', 'logo', 'ua', 'Referer', 'header'}
        for k, v in item.items():
            if k not in exclude_keys and v is not None:
                headers[k] = str(v)

        proxy = item.get('proxy', 'noproxy').lower() == 'proxy'

        cache_key = hashlib.md5(f"{url}{json.dumps(headers, sort_keys=True)}".encode()).hexdigest()
        content = self._get_ext_cached_content(cache_key)
        if content is None:
            try:
                resp = self._http_get_with_proxy(url, headers, proxy)
                if resp and resp.status_code == 200:
                    resp.encoding = 'utf-8'   # 强制 UTF-8 解码，避免乱码
                    content = resp.text
                    self._set_ext_cached_content(cache_key, content)
                else:
                    self._log(f"获取解析接口失败 {name}", {"status": resp.status_code if resp else 'no response'})
                    return
            except Exception as e:
                self._log(f"解析接口请求异常 {name}", {"error": repr(e)})
                return

        parsed = self._parse_remote_content(content, name, headers, proxy)
        for ch in parsed:
            self.ext_manager.add_channel(
                name=ch['name'],
                group=self._clean_group(ch['group']),
                url=ch['url'],
                headers=ch.get('headers', headers.copy()),
                proxy=ch.get('proxy', proxy),
                source=f'parse_{idx}'
            )
        self._log(f"解析接口 {name} 完成，解析到 {len(parsed)} 个频道")

    def _http_get_with_proxy(self, url, headers, proxy):
        if proxy and self.ytb_enabled:
            return self.session_ytb.get(url, headers=headers, timeout=30, verify=False)
        else:
            return self.session_ysp.get(url, headers=headers, timeout=30, verify=False)

    def _get_ext_cached_content(self, key):
        with self._ext_cache_lock:
            entry = self._ext_cache.get(key)
            if entry and time.time() - entry['time'] < Spider.EXTERNAL_CACHE_TTL:
                return entry['content']
        return None

    def _set_ext_cached_content(self, key, content):
        with self._ext_cache_lock:
            self._ext_cache[key] = {'content': content, 'time': time.time()}

    def _parse_remote_content(self, content, source_name, default_headers, default_proxy):
        """解析远程接口返回的内容（支持 M3U 和 TXT）"""
        channels = []
        if '#EXTM3U' in content:
            lines = content.splitlines()
            current_group = '默认分类'
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#EXTM3U') or line.startswith('#EXT-X-'):
                    i += 1
                    continue
                if line.startswith('#EXTINF:'):
                    info = line
                    group_match = re.search(r'group-title="([^"]+)"', info)
                    if group_match:
                        current_group = self._clean_group(group_match.group(1))
                    name_match = re.search(r',([^,]+)$', info)
                    ch_name = name_match.group(1).strip() if name_match else f"频道_{len(channels)}"
                    i += 1
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    if i < len(lines):
                        url = lines[i].strip()
                        if url and not url.startswith('#'):
                            channels.append({
                                'name': ch_name,
                                'group': current_group,
                                'url': url,
                                'headers': default_headers.copy(),
                                'proxy': default_proxy
                            })
                    i += 1
                else:
                    if ',' in line and not line.startswith('#'):
                        parts = line.split(',', 1)
                        ch_name = parts[0].strip()
                        url = parts[1].strip()
                        if ch_name and url and not url.startswith('#'):
                            channels.append({
                                'name': ch_name,
                                'group': current_group,
                                'url': url,
                                'headers': default_headers.copy(),
                                'proxy': default_proxy
                            })
                    i += 1
        else:
            lines = content.splitlines()
            current_group = '默认分类'
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '#genre#' in line:
                    parts = line.split(',')
                    grp = parts[0].strip()
                    if grp.startswith('#'):
                        grp = grp[1:].strip()
                    if grp:
                        current_group = self._clean_group(grp)
                    continue
                if ',' in line:
                    parts = line.split(',', 1)
                    ch_name = parts[0].strip()
                    url = parts[1].strip()
                    if ch_name and url and not url.startswith('#'):
                        channels.append({
                            'name': ch_name,
                            'group': current_group,
                            'url': url,
                            'headers': default_headers.copy(),
                            'proxy': default_proxy
                        })
        return channels

    # ==================== 动态代理检测（不变） ====================
    def _check_ytb_available(self):
        # 1. 优先尝试从 ext 传入的代理
        if hasattr(self, 'ext_proxies') and self.ext_proxies:
            for p in self.ext_proxies:
                test_proxies = {'http': p, 'https': p}
                try:
                    r = requests.get('https://www.youtube.com', proxies=test_proxies, timeout=2)
                    if r.status_code < 400:
                        self.session_ytb.proxies = test_proxies
                        self.ytb_enabled = True
                        self._log("ext代理检测成功", {"proxy": p})
                        return
                except Exception:
                    continue
            # 若所有 ext 代理均失败，继续尝试内置代理
            self._log("ext代理均不可用，尝试内置代理")
    
        # 2. 原有内置代理列表（保留）
        if self.session_ytb.proxies:
            # 原有已配置代理检测（保留）
            try:
                r = requests.get('https://www.youtube.com', proxies=self.session_ytb.proxies, timeout=2)
                if r.status_code < 400:
                    self.ytb_enabled = True
                    self._log("代理检测成功（已配置）")
                    return
            except Exception:
                pass
            self.session_ytb.proxies = {}
    
        default_proxies = [
            "http://127.0.0.1:2080", "http://127.0.0.1:7890", "http://127.0.0.1:10809",
            "http://127.0.0.1:20172", "http://127.0.0.1:10172", "http://127.0.0.1:7891",
            "http://127.0.0.1:10808", "http://127.0.0.1:1087", "http://127.0.0.1:3128",
            "http://127.0.0.1:1080", "http://127.0.0.1:8080", "http://127.0.0.1:9090"
        ]
        for p in default_proxies:
            test_proxies = {'http': p, 'https': p}
            try:
                r = requests.get('https://www.youtube.com', proxies=test_proxies, timeout=2)
                if r.status_code < 400:
                    self.session_ytb.proxies = test_proxies
                    self.ytb_enabled = True
                    self._log("内置代理检测成功", {"proxy": p})
                    return
            except Exception:
                continue
        self.session_ytb.proxies = {}
        self.ytb_enabled = False
        self._log("所有代理检测失败，YouTube功能禁用")

    def getName(self):
        return "央视频+YouTube台湾新闻+外部频道"

    # ==================== 动态生成播放列表 ====================
    def liveContent(self, url):
        self._check_ytb_available()

        lines = ['#EXTM3U']
        # ---- 1. 内置 YSP 频道 ----
        lines.append('\n=========内置ysp========,#genre#')
        groups = {}
        for ch in self.channels:
            if ch.get('is_ytb', False):
                continue
            groups.setdefault(ch['group'], []).append(ch)
        for group_name, ch_list in groups.items():
            lines.append(f'{group_name},#genre#')
            for ch in ch_list:
                name = ch['name'].replace('"', '\\"').replace(',', '\\,')
                lines.append(f'#EXTINF:-1 tvg-id="{ch["id"] if ch["id"] else name}" tvg-name="{name}" group-title="{group_name}",{name}')
                lines.append(ch['proxy_url'])

        # ---- 2. 内置 YTB 频道（仅当代理可用） ----
        if self.ytb_enabled:
            lines.append('\n=========内置ytb========,#genre#')
            ytb_groups = {}
            for ch in self.channels:
                if ch.get('is_ytb', False):
                    ytb_groups.setdefault(ch['group'], []).append(ch)
            for group_name, ch_list in ytb_groups.items():
                lines.append(f'{group_name},#genre#')
                for ch in ch_list:
                    name = ch['name'].replace('"', '\\"').replace(',', '\\,')
                    lines.append(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{name}" group-title="{group_name}",{name}')
                    lines.append(ch['proxy_url'])

        # ---- 3. 外部频道（直连 + 解析） ----
        if self.ext_manager.channels:
            source_groups = {}
            for ch in self.ext_manager.channels:
                source = ch['source']
                source_groups.setdefault(source, []).append(ch)

            for src, ch_list in source_groups.items():
                display_name = self._get_source_display_name(src)
                lines.append(f'\n========={display_name}========,#genre#')
                group_dict = {}
                for ch in ch_list:
                    group_dict.setdefault(ch['group'], []).append(ch)
                for group_name, items in group_dict.items():
                    num = self.ext_manager.get_group_number(src, group_name)
                    if num > 0:
                        group_title = f"{group_name}|{num}"
                    else:
                        group_title = group_name
                    lines.append(f'{group_title},#genre#')
                    for ch in items:
                        name = ch['name'].replace('"', '\\"').replace(',', '\\,')
                        if ch['headers'] or ch['proxy']:
                            proxy_url = f"http://127.0.0.1:9978/proxy?do=py&fun=external&id={ch['id']}"
                        else:
                            proxy_url = ch['url']
                        lines.append(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{name}" group-title="{group_name}",{name}')
                        lines.append(proxy_url)

        return '\n'.join(lines)

    def _get_source_display_name(self, source):
        if source == 'direct':
            return '直连频道'
        if source.startswith('parse_'):
            try:
                idx = int(source.split('_')[1])
                if idx < len(self._parse_names):
                    return self._parse_names[idx]
            except:
                pass
            return f'解析接口{idx+1}'
        return '外部频道'
        
    # ==================== 路由处理 ====================
    def localProxy(self, params):
        fun = params.get('fun')
        if fun == 'cctv':
            return self._handle_ysp(params)
        elif fun == 'yttv':
            return self._handle_ytb(params)
        elif fun == 'ts':
            return self._handle_ts(params)
        elif fun == 'external':
            return self._handle_external(params)
        else:
            return self._error_response("未知请求")
    
    # ==================== 外部频道代理处理 ====================
    def _handle_external(self, params):
        ch_id = params.get('id')
        if not ch_id:
            return self._error_response("缺少频道ID")
        ch = self.ext_manager.get_channel_by_id(ch_id)
        if not ch:
            return self._error_response("无效的频道ID")
    
        if 'ts' in params:
            ts_url = self._b64_decode(params['ts'])
            try:
                if ch['proxy'] and self.ytb_enabled:
                    resp = self.session_ytb.get(ts_url, headers=ch['headers'], timeout=30, verify=False)
                else:
                    resp = self.session_ysp.get(ts_url, headers=ch['headers'], timeout=30, verify=False)
                if resp.status_code != 200:
                    return self._error_response(f"TS 请求失败 {resp.status_code}")
                return [200, "video/MP2T", resp.content, {
                    'Content-Type': 'video/MP2T',
                    'Content-Length': str(len(resp.content)),
                    'Cache-Control': 'no-cache'
                }]
            except Exception as e:
                return self._error_response(f"TS 代理异常: {str(e)}")
    
        url = ch['url']
        headers = ch['headers']
        proxy = ch['proxy']
    
        try:
            if proxy and self.ytb_enabled:
                resp = self.session_ytb.get(url, headers=headers, timeout=30, verify=False)
            else:
                resp = self.session_ysp.get(url, headers=headers, timeout=30, verify=False)
    
            if resp.status_code != 200:
                return self._error_response(f"外部频道请求失败 {resp.status_code}")
    
            content_type = resp.headers.get('Content-Type', '')
            if 'mpegurl' in content_type or 'application/vnd.apple.mpegurl' in content_type or '#EXTM3U' in resp.text[:1000]:
                m3u8_content = self._rewrite_external_m3u8(resp.text, ch_id, url)
                return [200, "application/vnd.apple.mpegurl", m3u8_content]
            else:
                return [200, resp.headers.get('Content-Type', 'application/octet-stream'), resp.content, {
                    'Content-Type': resp.headers.get('Content-Type', 'application/octet-stream'),
                    'Content-Length': str(len(resp.content)),
                    'Cache-Control': 'no-cache'
                }]
        except Exception as e:
            self._log("外部频道请求异常", {"id": ch_id, "error": repr(e)})
            return self._error_response(f"请求异常: {str(e)}")
    
    def _rewrite_external_m3u8(self, text, ch_id, base_url):
        lines = text.splitlines()
        rewritten = []
        for line in lines:
            if line.startswith('#'):
                rewritten.append(line)
            else:
                ts_url = urljoin(base_url, line.strip())
                encoded_ts = self._b64_encode(ts_url)
                proxy_ts = f"http://127.0.0.1:9978/proxy?do=py&fun=external&id={ch_id}&ts={encoded_ts}"
                rewritten.append(proxy_ts)
        return '\n'.join(rewritten) + '\n'
    
    # ==================== YSP 处理器（完整复制原逻辑） ====================
    def _get_cache_lock(self, cache_key):
        with Spider._lock_dict_lock:
            if cache_key not in Spider._lock_dict:
                Spider._lock_dict[cache_key] = threading.Lock()
            return Spider._lock_dict[cache_key]
    
    def _get_fail_count(self, cache_key):
        with Spider._fail_count_lock:
            return Spider._fail_count_dict.get(cache_key, 0)
    
    def _reset_fail_count(self, cache_key):
        with Spider._fail_count_lock:
            Spider._fail_count_dict[cache_key] = 0
    
    def _increment_fail_count(self, cache_key):
        with Spider._fail_count_lock:
            Spider._fail_count_dict[cache_key] = Spider._fail_count_dict.get(cache_key, 0) + 1
            return Spider._fail_count_dict[cache_key]
    
    def _clear_fail_count(self, cache_key):
        with Spider._fail_count_lock:
            if cache_key in Spider._fail_count_dict:
                del Spider._fail_count_dict[cache_key]
    
    def _cache_path(self, cache_key):
        return os.path.join(Spider.CACHE_DIR, hashlib.md5(cache_key.encode()).hexdigest() + '.cache')
    
    def _get_cached_playurl(self, cache_key):
        cache_file = self._cache_path(cache_key)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    playurl = data.get('playurl')
                    playurl_time = data.get('playurl_time', 0)
                    now = time.time()
                    if playurl and (now - playurl_time) < Spider.CACHE_TTL:
                        fail_cnt = self._get_fail_count(cache_key)
                        if fail_cnt < 3:
                            return playurl, True
                        else:
                            self._clear_cache_file(cache_key)
                            return None, False
                    else:
                        return None, False
            except Exception:
                return None, False
        return None, False
    
    def _set_cached_playurl(self, cache_key, playurl):
        cache_file = self._cache_path(cache_key)
        data = {
            'playurl': playurl,
            'playurl_time': int(time.time())
        }
        try:
            tmp_file = cache_file + '.tmp'
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            os.replace(tmp_file, cache_file)
            self._reset_fail_count(cache_key)
            self._clean_cache()
        except Exception:
            pass
    
    def _clear_cache_file(self, cache_key):
        cache_file = self._cache_path(cache_key)
        try:
            if os.path.exists(cache_file):
                os.remove(cache_file)
        except Exception:
            pass
    
    def _clean_cache(self):
        now = time.time()
        try:
            for fname in os.listdir(Spider.CACHE_DIR):
                filepath = os.path.join(Spider.CACHE_DIR, fname)
                if os.path.isfile(filepath):
                    mtime = os.path.getmtime(filepath)
                    if now - mtime > (Spider.CACHE_TTL * 2):
                        os.remove(filepath)
        except Exception:
            pass
    
    def _get_cached_m3u8(self, cache_key):
        with self._m3u8_cache_lock:
            entry = self._m3u8_cache.get(cache_key)
            if entry:
                content, timestamp = entry['content'], entry['time']
                if time.time() - timestamp < Spider.M3U8_CONTENT_CACHE_TTL:
                    return content, True
        return None, False
    
    def _set_cached_m3u8(self, cache_key, content):
        with self._m3u8_cache_lock:
            self._m3u8_cache[cache_key] = {'content': content, 'time': time.time()}
    
    def _fetch_and_fix_ysp_m3u8(self, play_url):
        try:
            headers = {
                'connection': 'Keep-Alive',
                'Range': 'bytes=0-',
                'accept-encoding': 'gzip',
                'user-agent': 'qqlive',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            resp = self.session_ysp.get(play_url, headers=headers, timeout=20, verify=False)
            if resp.status_code != 200:
                return None
    
            content = resp.text
            if '#EXTM3U' not in content:
                return None
    
            parsed = urlparse(play_url)
            base = f"{parsed.scheme}://{parsed.netloc}{parsed.path[:parsed.path.rfind('/')+1]}"
    
            fixed_lines = []
            for line in content.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and '.ts' in stripped:
                    if not stripped.startswith(('http://', 'https://')):
                        ts_url = urljoin(base, stripped)
                    else:
                        ts_url = stripped
                    fixed_lines.append(ts_url)
                else:
                    fixed_lines.append(line)
    
            return '\n'.join(fixed_lines)
        except Exception:
            return None
    
    def _handle_ysp(self, params):
        cnlid = params.get('cnlid')
        livepid = params.get('livepid')
        defn = params.get('defn', 'fhd')
    
        if not cnlid or not livepid:
            return self._error_response("央视频缺少参数 cnlid 或 livepid")
    
        cache_key = f"ysp_{cnlid}_{livepid}_{defn}"
        lock = self._get_cache_lock(cache_key)
        with lock:
            cached_m3u8, valid = self._get_cached_m3u8(cache_key)
            if valid and cached_m3u8:
                return [200, "application/vnd.apple.mpegurl", cached_m3u8]
    
            playurl, valid = self._get_cached_playurl(cache_key)
            if valid and playurl:
                for attempt in range(3):
                    m3u8_content = self._fetch_and_fix_ysp_m3u8(playurl)
                    if m3u8_content:
                        self._reset_fail_count(cache_key)
                        self._set_cached_m3u8(cache_key, m3u8_content)
                        return [200, "application/vnd.apple.mpegurl", m3u8_content]
                    else:
                        fail_cnt = self._increment_fail_count(cache_key)
                        if fail_cnt >= 3:
                            self._clear_cache_file(cache_key)
                            self._clear_fail_count(cache_key)
                            break
                        time.sleep(0.2)
                old_m3u8, _ = self._get_cached_m3u8(cache_key)
                if old_m3u8:
                    return [200, "application/vnd.apple.mpegurl", old_m3u8]
                self._clear_cache_file(cache_key)
    
            manager = CKeyManager()
            new_playurl = manager.get_play_url(cnlid, livepid, defn)
            if not new_playurl:
                return self._error_response("获取播放地址失败")
    
            m3u8_content = self._fetch_and_fix_ysp_m3u8(new_playurl)
            if not m3u8_content:
                return self._error_response("获取 m3u8 失败")
    
            self._set_cached_playurl(cache_key, new_playurl)
            self._set_cached_m3u8(cache_key, m3u8_content)
            return [200, "application/vnd.apple.mpegurl", m3u8_content]
    
    # ==================== YTB 处理器 ====================
    def _handle_ytb(self, params):
        vid = params.get('id')
        if not vid or vid not in self.ytb_url_map:
            return self._error_response("无效的 YouTube 频道ID")
    
        if not self.ytb_enabled:
            return self._error_response("代理不可用，无法获取 YouTube 直播")
    
        now = time.time()
        if vid in self.fail_cache and self.fail_cache[vid] > now:
            return self._error_response("该频道暂时无法获取直播流")
    
        cached_m3u8 = self.m3u8_cache.get(vid)
        if cached_m3u8 and cached_m3u8.get('expires', 0) > now:
            return [200, "application/vnd.apple.mpegurl", cached_m3u8['content']]
    
        video_info = self.video_cache.get(vid)
        if not video_info or video_info.get('expires', 0) <= now:
            info = self._get_ytb_video_info(vid)
            if not info:
                self.fail_cache[vid] = now + 120
                return self._error_response("无法获取 YouTube 直播视频")
            self.video_cache[vid] = {
                'video_id': info['video_id'],
                'hls_url': info['hls_url'],
                'expires': now + 300
            }
            video_info = self.video_cache[vid]
    
        m3u8_content = self._fetch_and_rewrite_ytb_m3u8(video_info['hls_url'], vid)
        if not m3u8_content:
            self.fail_cache[vid] = now + 120
            return self._error_response("获取 YouTube M3U8 失败")
    
        self.m3u8_cache[vid] = {'content': m3u8_content, 'expires': now + 15}
        return [200, "application/vnd.apple.mpegurl", m3u8_content]
    
    def _get_ytb_video_info(self, vid):
        url = self.ytb_url_map[vid]
        if 'watch?v=' in url or 'youtu.be/' in url:
            try:
                video_id = YouTubeLiveLite.extract_video_id(url)
                data = self.yt.extract_live(video_id)
                if data.get('is_live') and data.get('hls_url'):
                    return {'video_id': video_id, 'hls_url': data['hls_url']}
                return None
            except Exception:
                return None
    
        if 'm.youtube.com' in url:
            url = url.replace('m.youtube.com', 'www.youtube.com')
        try:
            parsed = urlparse(url)
            encoded_path = quote(parsed.path, safe='/')
            url = urlunparse((parsed.scheme, parsed.netloc, encoded_path, parsed.params, parsed.query, parsed.fragment))
        except Exception:
            pass
    
        try:
            resp = self.session_ytb.get(url, timeout=30)
            resp.raise_for_status()
            html_text = resp.text
        except Exception:
            return None
    
        video_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', html_text)
        if not video_ids:
            return None
    
        seen = set()
        for vid in video_ids:
            if vid in seen:
                continue
            seen.add(vid)
            try:
                data = self.yt.extract_live(vid)
                if data.get('is_live') and data.get('hls_url'):
                    return {'video_id': vid, 'hls_url': data['hls_url']}
            except Exception:
                continue
        return None
    
    def _fetch_and_rewrite_ytb_m3u8(self, hls_url, channel_id):
        try:
            resp = self.session_ytb.get(hls_url, headers={
                'User-Agent': 'com.google.android.youtube/21.02.35 (Linux; U; Android 11) gzip',
                'Referer': 'https://www.youtube.com/',
            }, timeout=30)
            resp.raise_for_status()
            text = resp.text
        except Exception:
            return None
    
        if '#EXT-X-STREAM-INF' in text:
            variant_url = self._pick_best_variant(hls_url, text)
            if not variant_url:
                return None
            try:
                resp = self.session_ytb.get(variant_url, headers={
                    'User-Agent': 'com.google.android.youtube/21.02.35 (Linux; U; Android 11) gzip',
                    'Referer': 'https://www.youtube.com/',
                }, timeout=30)
                resp.raise_for_status()
                text = resp.text
            except Exception:
                return None
    
        rewritten = []
        for line in text.splitlines():
            if line.startswith('#'):
                rewritten.append(line)
            else:
                ts_url = urljoin(hls_url, line.strip())
                encoded = self._b64_encode(ts_url)
                proxy_ts = f"http://127.0.0.1:9978/proxy?do=py&fun=ts&url={encoded}&channel={channel_id}"
                rewritten.append(proxy_ts)
        return '\n'.join(rewritten) + '\n'
    
    def _pick_best_variant(self, base_url, text):
        lines = text.splitlines()
        best_score = -1
        best_url = ''
        for i, line in enumerate(lines):
            if not line.startswith('#EXT-X-STREAM-INF'):
                continue
            bandwidth = re.search(r'BANDWIDTH=(\d+)', line)
            resolution = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
            score = 0
            if bandwidth:
                score += int(bandwidth.group(1))
            if resolution:
                score += int(resolution.group(1)) * int(resolution.group(2))
            for j in range(i + 1, len(lines)):
                if not lines[j].strip() or lines[j].startswith('#'):
                    continue
                if score > best_score:
                    best_score = score
                    best_url = urljoin(base_url, lines[j].strip())
                break
        return best_url
    
    def _handle_ts(self, params):
        b64_url = params.get('url', '')
        if not b64_url:
            return self._error_response("缺少 TS URL")
        try:
            ts_url = self._b64_decode(b64_url)
        except:
            return self._error_response("TS URL 解码失败")
    
        try:
            resp = self.session_ytb.get(ts_url, headers={
                'User-Agent': 'com.google.android.youtube/21.02.35 (Linux; U; Android 11) gzip',
                'Accept': '*/*',
                'Referer': 'https://www.youtube.com/',
            }, timeout=30)
            if resp.status_code != 200:
                return self._error_response(f"TS 请求失败 {resp.status_code}")
            return [200, "video/MP2T", resp.content, {
                'Content-Type': 'video/MP2T',
                'Content-Length': str(len(resp.content)),
                'Cache-Control': 'no-cache'
            }]
        except Exception as e:
            return self._error_response(f"TS 代理异常: {str(e)}")
    
    def _b64_encode(self, s):
        return base64.urlsafe_b64encode(s.encode()).decode().rstrip('=')
    
    def _b64_decode(self, s):
        padding = 4 - (len(s) % 4)
        if padding != 4:
            s += '=' * padding
        return base64.urlsafe_b64decode(s).decode()
    
    def _error_response(self, msg):
        error_m3u = (
            "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-MEDIA-SEQUENCE:0\n"
            "#EXT-X-TARGETDURATION:10\n#EXTINF:10.0,\nerror.ts\n"
            f"#EXT-X-ENDLIST\n# {msg}"
        )
        return [500, "application/vnd.apple.mpegurl", error_m3u]
    
    def destroy(self):
        if self.session_ytb:
            self.session_ytb.close()
        if self.session_ysp:
            self.session_ysp.close()
        self._log("Spider destroyed")