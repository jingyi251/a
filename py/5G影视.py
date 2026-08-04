#!/usr/bin/python
# -*- coding: utf-8 -*-
import re,json,html,requests
from urllib.parse import quote
from lxml import etree
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider: pass

class Spider(BaseSpider):
    def getName(self): return '5G影视'
    def init(self,extend=''):
        self.host='https://5gysh.cc'
        self.headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36','Referer':self.host+'/','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8','Accept-Language':'zh-CN,zh;q=0.9'}
        self.categories=[]; self.filters={}
    def _ensure(self):
        if not hasattr(self,'host'): self.init()
    def _get(self,url):
        self._ensure()
        try:
            r=requests.get(url,headers=self.headers,timeout=15); r.encoding='utf-8'; return r.text
        except Exception as e:
            print(f'[5G影视] 请求失败: {url} - {e}'); return ''
    def _tree(self,s):
        try: return etree.HTML(s) if s else None
        except Exception: return None
    def _fix(self,u):
        self._ensure()
        if not u: return ''
        u=html.unescape(str(u)).strip()
        if u.startswith('//'): return 'https:'+u
        if u.startswith('/'): return self.host+u
        return u
    def _clean(self,s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',str(s or '')))).strip()
    def _pick_pic(self,vals):
        for v in vals:
            v=str(v or '').strip()
            if v and 'loading' not in v and 'favicon' not in v: return self._fix(v)
        return ''
    def _parse_nav(self,t):
        classes=[]; filters={}
        navs=t.xpath('//li[contains(@class,"nav-item") and contains(@class,"dropdown")]') if t is not None else []
        for nav in navs:
            ph=''.join(nav.xpath('./a[contains(@class,"dropdown-toggle")]/@href')).strip(); pn=self._clean(''.join(nav.xpath('./a[contains(@class,"dropdown-toggle")]//text()')))
            if not pn or 'category' not in ph: continue
            raw=ph.strip('/').split('/')[-1]; tid=raw.replace('cate','') if raw.startswith('cate') else raw
            vals=[]
            for a in nav.xpath('.//ul[contains(@class,"dropdown-menu")]//a[contains(@class,"dropdown-item")]'):
                href=''.join(a.xpath('./@href')).strip(); name=self._clean(''.join(a.xpath('.//text()'))); sid=href.strip('/').split('/')[-1].replace('cate','')
                if sid and name: vals.append({'n':name,'v':sid})
            classes.append({'type_id':tid,'type_name':pn}); filters[tid]=[{'key':'sub','name':'分类','value':vals}] if vals else []
        if not classes:
            classes=[{'type_id':'boutique','type_name':'热播'},{'type_id':'recommend','type_name':'推荐'},{'type_id':'19','type_name':'分类1'},{'type_id':'91','type_name':'分类2'},{'type_id':'106','type_name':'分类3'},{'type_id':'120','type_name':'分类4'}]
            filters={'boutique':[{'key':'sub','name':'分类','value':[{'n':'每日更新','v':'33'},{'n':'精选','v':'34'},{'n':'热门','v':'40'}]}],'recommend':[],'19':[],'91':[],'106':[],'120':[]}
        return classes,filters
    def _parse_list(self,s):
        t=self._tree(s); arr=[]; seen=set()
        if t is None: return arr
        items=t.xpath('//main//a[contains(@href,"/video/") and .//img]')
        if not items: items=t.xpath('//a[contains(@href,"/video/") and .//img]')
        if not items: items=t.xpath('//a[contains(@href,"/video/") and contains(@onclick,"clickDD")]')
        if not items: items=t.xpath('//a[contains(@href,"/video/")]')
        print(f'[5G影视] 列表匹配到 {len(items)} 个视频元素')
        for a in items:
            try:
                href=''.join(a.xpath('./@href')).strip(); m=re.search(r'/video/([^/]+)/?',href)
                if not m: continue
                vid=m.group(1)
                if not vid.isdigit() or vid in seen: continue
                seen.add(vid)
                name=self._clean(''.join(a.xpath('.//h3/text()')) or ''.join(a.xpath('.//img/@alt')) or ''.join(a.xpath('./@aria-label'))).rsplit('-',1)[0]
                pic=self._pick_pic(a.xpath('.//img/@data-src | .//img/@data-original | .//img/@data-cover | .//img/@src'))
                remark=self._clean(''.join(a.xpath('.//*[contains(@class,"duration")]/text() | .//*[contains(@class,"kicker")]/text()')))
                arr.append({'vod_id':vid,'vod_name':name or '视频'+vid,'vod_pic':pic,'vod_remarks':remark})
            except Exception: continue
        return arr
    def homeContent(self,filter):
        try:
            h=self._get(self.host+'/'); t=self._tree(h); self.categories,self.filters=self._parse_nav(t); return {'class':self.categories,'filters':self.filters,'list':self._parse_list(h)}
        except Exception as e:
            print(f'[5G影视] 首页失败: {e}'); return {'class':[],'filters':{},'list':[]}
    def homeVideoContent(self): return {'list':self._parse_list(self._get(self.host+'/'))}
    def _first_sub(self,tid):
        try:
            if not self.filters:
                h=self._get(self.host+'/'); t=self._tree(h); self.categories,self.filters=self._parse_nav(t)
            fs=self.filters.get(str(tid)) or []
            vals=fs[0].get('value',[]) if fs else []
            return str(vals[0].get('v','')) if vals else ''
        except Exception: return ''
    def categoryContent(self,tid,pg,filter,extend):
        try:
            sub=(extend.get('sub') if isinstance(extend,dict) else '') or ''
            if not sub: sub=self._first_sub(tid)
            cid=str(sub or tid).replace('cate','')
            path=(f'/category/{tid}/' if str(pg)=='1' else f'/category/{tid}/{pg}/') if str(tid) in ['boutique','recommend'] and not sub else (f'/category/cate{cid}/' if str(pg)=='1' else f'/category/cate{cid}/{pg}/')
            return {'page':int(pg),'pagecount':999,'limit':20,'total':9999,'list':self._parse_list(self._get(self.host+path))}
        except Exception as e:
            print(f'[5G影视] 分类失败: {e}'); return {'page':int(pg),'pagecount':1,'limit':20,'total':0,'list':[]}
    def detailContent(self,ids):
        out=[]
        for vid in ids:
            try:
                v=str(vid).strip('/').split('/')[-1]; url=self.host+'/video/'+v; h=self._get(url); t=self._tree(h)
                if not h or '页面不存在' in h: continue
                name=self._clean(''.join(t.xpath('//h1/text()')) if t is not None else '') or self._clean(re.search(r'<title>(.*?)</title>',h,re.S).group(1) if re.search(r'<title>(.*?)</title>',h,re.S) else '')
                pic=self._pick_pic(t.xpath('//meta[@property="og:image"]/@content | //img[contains(@class,"poster") or contains(@class,"cover") or contains(@class,"thumb")]/@src | //div[contains(@class,"player") or contains(@class,"video")]//img/@src') if t is not None else [])
                play=url; cfg=re.search(r'window\.__ARCHIVE_PLAYER__\s*=\s*(\{.*?\});',h,re.S)
                if cfg:
                    try:
                        data=json.loads(cfg.group(1)); raw=data.get('rawPath') or data.get('path') or data.get('url') or ''; cdn=data.get('cdnLine') or ''; pic=pic or self._fix(data.get('posterImg','')); play=(cdn.rstrip('/')+'/'+raw.lstrip('/')) if raw and not raw.startswith('http') and cdn else self._fix(raw) if raw else url
                    except Exception: pass
                out.append({'vod_id':v,'vod_name':name or '视频'+v,'vod_pic':pic,'vod_content':name,'vod_play_from':'5G影视','vod_play_url':'正片$'+play})
            except Exception as e:
                print(f'[5G影视] 详情失败: {vid} - {e}'); continue
        return {'list':out}
    def searchContent(self,key,quick,pg='1'):
        try:
            path=f'/search/{quote(key)}/' if str(pg)=='1' else f'/search/{quote(key)}/{pg}/'
            return {'page':int(pg),'pagecount':999,'limit':20,'total':9999,'list':self._parse_list(self._get(self.host+path))}
        except Exception as e:
            print(f'[5G影视] 搜索失败: {e}'); return {'list':[]}
    def playerContent(self,flag,id,vipFlags):
        try:
            u=self._fix(id)
            if '.m3u8' not in u and '.mp4' not in u:
                h=self._get(u); cfg=re.search(r'window\.__ARCHIVE_PLAYER__\s*=\s*(\{.*?\});',h,re.S)
                if cfg:
                    data=json.loads(cfg.group(1)); raw=data.get('rawPath') or data.get('path') or data.get('url') or ''; cdn=data.get('cdnLine') or ''; u=(cdn.rstrip('/')+'/'+raw.lstrip('/')) if raw and not raw.startswith('http') and cdn else self._fix(raw) if raw else u
                else:
                    m=re.search(r'(https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*)',h) or re.search(r'["\'](?:url|src)["\']\s*:\s*["\']([^"\']+)["\']',h)
                    if m: u=self._fix(m.group(1))
            return {'parse':0,'playUrl':'','url':u,'header':json.dumps({'User-Agent':self.headers['User-Agent'],'Referer':self.host+'/'})}
        except Exception as e:
            print(f'[5G影视] 播放失败: {e}'); return {'parse':0,'playUrl':'','url':id,'header':json.dumps(self.headers)}
    def isVideoFormat(self,url): return False
    def manualVideoCheck(self): return False
    def localProxy(self,param): return [404,'text/plain','']
    def destroy(self): pass
