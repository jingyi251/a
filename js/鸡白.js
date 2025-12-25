let host = 'https://www.jibai5.com';
let headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": host + "/"
};

async function init(cfg) {}

// 辅助函数 - 解析HTML
function pdfa(html, selector) {
    let results = [];
    
    if (selector === ".listfl") {
        // 匹配列表项
        let regex = /<li[^>]*class="[^"]*listfl[^"]*"[^>]*>([\s\S]*?)<\/li>/g;
        let match;
        while ((match = regex.exec(html)) !== null) {
            results.push(match[0]);
        }
    } else if (selector === ".dslist-group li") {
        // 匹配播放列表项
        let regex = /<li>([\s\S]*?)<\/li>/g;
        let match;
        while ((match = regex.exec(html)) !== null) {
            results.push(match[0]);
        }
    }
    
    return results;
}

// 解析视频列表
function getList(html) {
    let videos = [];
    let items = pdfa(html, ".listfl");
    
    items.forEach(it => {
        let idMatch = it.match(/href="\/voddetail\/(\d+)\.html"/);
        if (!idMatch) return;
        
        let nameMatch = it.match(/title="(.*?)"/);
        if (!nameMatch) {
            nameMatch = it.match(/<p[^>]*class="[^"]*list-name[^"]*"[^>]*>(.*?)<\/p>/);
        }
        
        let picMatch = it.match(/data-original="(.*?)"/);
        if (!picMatch || picMatch[1].includes('lazyload')) {
            picMatch = it.match(/src="(.*?)"/);
        }
        
        let remarkMatch = it.match(/<div[^>]*class="[^"]*duration[^"]*"[^>]*>(.*?)<\/div>/);
        
        if (idMatch && nameMatch) {
            let vpic = picMatch ? picMatch[1] : "";
            if (vpic) {
                if (vpic.startsWith('//')) {
                    vpic = 'http:' + vpic;
                } else if (vpic.startsWith('/')) {
                    vpic = host + vpic;
                }
            }
            
            videos.push({
                "vod_id": idMatch[1],
                "vod_name": nameMatch[1].trim(),
                "vod_pic": vpic,
                "vod_remarks": remarkMatch ? remarkMatch[1].trim() : ""
            });
        }
    });
    
    return videos;
}

// 首页分类
async function home(filter) {
    let classes = [
        {"type_name": "首页", "type_id": "home"},
        {"type_name": "3D国漫", "type_id": "20"},
        {"type_name": "动态漫", "type_id": "21"}, 
        {"type_name": "沙雕剧场", "type_id": "22"}
    ];
    return JSON.stringify({ class: classes });
}

// 首页推荐
async function homeVod() {
    let resp = await req(host, { headers: headers });
    return JSON.stringify({ list: getList(resp.content) });
}

// 分类页
async function category(tid, pg, filter, extend) {
    let p = pg || 1;
    let url = "";
    
    if (tid === "home") {
        url = host;
    } else {
        if (p === 1) {
            url = host + "/vodtype/" + tid + ".html";
        } else {
            url = host + "/vodtype/" + tid + "-" + p + ".html";
        }
    }
    
    let resp = await req(url, { headers: headers });
    let list = getList(resp.content);
    
    return JSON.stringify({ 
        list: list, 
        page: parseInt(p),
        total: 999,
        limit: 30,
        pagecount: 50
    });
}

// 详情页
async function detail(id) {
    let url = host + '/voddetail/' + id + '.html';
    let resp = await req(url, { headers: headers });
    let html = resp.content;
    
    // 提取基本信息
    let nameMatch = html.match(/<title>([^<]+)<\/title>/);
    let vodName = nameMatch ? nameMatch[1].replace(/[_-].+$/, "").trim() : "未知";
    
    // 提取图片
    let picMatch = html.match(/data-original="(.*?)"/) || 
                   html.match(/<img[^>]*class="[^"]*lazy[^"]*"[^>]*src="([^"]+)"[^>]*>/);
    
    // 提取状态/更新集数
    let statusMatch = html.match(/<span>(\d+D大作更至\d+|\d+集全|沙雕番更至\d+)<\/span>/);
    
    // 提取简介
    let descMatch = html.match(/剧情：<p>([\s\S]*?)<\/p>/);
    if (!descMatch) {
        descMatch = html.match(/<p>([^<]+\.\.\.)<\/p>/);
    }
    
    // 提取播放列表
    let playList = [];
    let playItems = pdfa(html, ".dslist-group li");
    
    playItems.forEach(item => {
        let linkMatch = item.match(/href="\/vodplay\/([^"]+)"/);
        let titleMatch = item.match(/title="([^"]+)"/);
        
        if (linkMatch && titleMatch) {
            let playId = linkMatch[1]; // 格式：446-1-1
            let episodeName = titleMatch[1];
            playList.push(episodeName + "$" + playId);
        }
    });
    
    // 如果没有找到播放列表，创建默认集数
    if (playList.length === 0) {
        for (let i = 1; i <= 10; i++) {
            playList.push("第" + i + "集$" + id + "-1-" + i);
        }
    }
    
    let vod = {
        'vod_id': id,
        'vod_name': vodName,
        'vod_pic': picMatch ? picMatch[1] : "",
        'vod_content': descMatch ? descMatch[1].replace(/<[^>]*>/g, "").trim() : "暂无简介",
        'vod_remarks': statusMatch ? statusMatch[1] : "",
        'vod_play_from': "官方线路",
        'vod_play_url': playList.join('#')
    };
    
    return JSON.stringify({ list: [vod] });
}

// 搜索功能
async function search(wd, quick, pg) {
    let url = host + '/vodsearch/' + encodeURIComponent(wd) + '-------------.html';
    let resp = await req(url, { headers: headers });
    
    // 搜索页使用相同的列表解析
    let videos = getList(resp.content);
    
    return JSON.stringify({ list: videos });
}

// 播放页 - 提取直链
async function play(flag, id, flags) {
    // id格式：视频ID-线路-集数，如：446-1-1
    let playId = id;
    
    // 构建播放页URL
    let url = host + "/vodplay/" + playId + ".html";
    
    try {
        let resp = await req(url, { headers: headers });
        let html = resp.content;
        
        // 方法1：从JavaScript变量中提取MP4地址
        let jsMatch = html.match(/"url":"([^"]+\.mp4[^"]*)"/);
        if (jsMatch) {
            let mp4Url = jsMatch[1].replace(/\\/g, "");
            return JSON.stringify({
                parse: 0,
                url: mp4Url,
                header: headers
            });
        }
        
        // 方法2：从脚本内容中提取
        let scriptMatch = html.match(/var player_aaaa=\{[\s\S]*?"url":"([^"]+)"[\s\S]*?\}/);
        if (scriptMatch) {
            let mp4Url = scriptMatch[1].replace(/\\/g, "");
            return JSON.stringify({
                parse: 0,
                url: mp4Url,
                header: headers
            });
        }
        
        // 方法3：直接查找mp4链接
        let mp4Match = html.match(/https:\/\/[^"]+\.mp4/);
        if (mp4Match) {
            return JSON.stringify({
                parse: 0,
                url: mp4Match[0],
                header: headers
            });
        }
        
        // 如果没有找到直接地址，返回播放页让播放器解析
        return JSON.stringify({
            parse: 1,
            url: url,
            header: headers
        });
    } catch (e) {
        // 如果出错，直接返回播放页
        return JSON.stringify({
            parse: 1,
            url: url,
            header: headers
        });
    }
}

export default { init, home, homeVod, category, detail, search, play };