/*!
 * @name 星海音乐源
 * @description 基于GD Studio API和TuneHub API的双引擎聚合音乐播放源，支持网易云、QQ、酷狗、酷我、咪咕五大平台
 * @version v2.2.7
 * @author 万去了了
 * @homepage https://zrcdy.dpdns.org/
 * @updateUrl https://zrcdy.dpdns.org/lx/xinghai-music-source.js
 * @feedback cdy123456_2021@qq.com
 * @lastUpdate 2025-12-31
 */

// ============================ 核心配置区域 ============================
const UPDATE_CONFIG = {
  // PHP版本检查接口
  versionApiUrl: 'https://zrcdy.dpdns.org/lx/version.php',
  latestScriptUrl: 'https://zrcdy.dpdns.org/lx/index.html',
  currentVersion: 'v2.2.7'
};

// 主API接口 - GD Studio
const MAIN_API_URL = 'https://music-api.gdstudio.xyz/api.php?use_xbridge3=true&loader_name=forest&need_sec_link=1&sec_link_scene=im&theme=light';

// 备用API接口 - TuneHub
const BACKUP_API_URL = 'https://music-dl.sayqz.com/api/';

// ============================ 全局状态变量 ============================
let musicSourceEnabled = true;
let serverCheckCompleted = false;

// ============================ 平台映射配置 ============================
// 主API平台映射
const MAIN_API_SOURCE_MAP = {
  wy: 'netease',
  tx: 'tencent',
  kw: 'kuwo',
  kg: 'kugou',
  mg: 'migu'
};

// 备用API平台映射
const BACKUP_API_SOURCE_MAP = {
  wy: 'netease',
  tx: 'qq',
  kw: 'kuwo'
};

// 音质支持配置
const MUSIC_QUALITY = {
  wy: ['128k', '192k', '320k', 'flac', 'flac24bit'],
  tx: ['128k', '192k', '320k', 'flac', 'flac24bit'],
  kw: ['128k', '192k', '320k', 'flac', 'flac24bit'],
  kg: ['128k', '192k', '320k', 'flac', 'flac24bit'],
  mg: ['128k', '192k', '320k', 'flac']
};

const { EVENT_NAMES, request, on, send } = globalThis.lx;
const MUSIC_SOURCE = Object.keys(MUSIC_QUALITY);

// ============================ 工具函数集 ============================
function log(...args) {
  console.log(...args);
}

function logSimple(action, source, musicInfo, status, extra = '') {
  const songName = musicInfo.name || '未知歌曲';
  log(`[${action}] 平台:${source} | 歌曲:${songName} | 状态:${status}${extra ? ' | ' + extra : ''}`);
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 音质映射和降级处理
 */
function mapQuality(targetQuality, availableQualities) {
  const qualityPriority = {
    '臻品母带': 'flac24bit',
    '臻品音质2.0': 'flac24bit', 
    '臻品音质': 'flac24bit',
    'Hires 无损24-Bit': 'flac24bit',
    'FLAC': 'flac',
    '320k': '320k',
    '192k': '192k',
    '128k': '128k'
  };
  
  if (availableQualities.includes(targetQuality)) {
    return targetQuality;
  }
  
  const mappedQuality = qualityPriority[targetQuality];
  if (mappedQuality && availableQualities.includes(mappedQuality)) {
    return mappedQuality;
  }
  
  const priorityOrder = ['flac24bit', 'flac', '320k', '192k', '128k'];
  for (const quality of priorityOrder) {
    if (availableQualities.includes(quality)) {
      return quality;
    }
  }
  
  return availableQualities[0] || '128k';
}

/**
 * 封装HTTP请求
 */
const httpFetch = (url, options = { method: 'GET' }) => {
  return new Promise((resolve, reject) => {
    const cancelRequest = request(url, options, (err, resp) => {
      if (err) {
        return reject(new Error(`网络请求异常：${err.message}`));
      }
      
      let responseBody = resp.body;
      if (typeof responseBody === 'string') {
        const trimmedBody = responseBody.trim();
        if (trimmedBody.startsWith('{') || trimmedBody.startsWith('[') || trimmedBody.startsWith('"')) {
          try {
            responseBody = JSON.parse(trimmedBody);
          } catch (e) {
            // 保持原始格式
          }
        }
      }
      
      resolve({
        body: responseBody,
        statusCode: resp.statusCode,
        headers: resp.headers || {}
      });
    });
  });
};

/**
 * 版本号比对
 */
const compareVersions = (remoteVer, currentVer) => {
  const remoteParts = remoteVer.replace(/^v/, '').split('.').map(Number);
  const currentParts = currentVer.replace(/^v/, '').split('.').map(Number);
  
  for (let i = 0; i < Math.max(remoteParts.length, currentParts.length); i++) {
    const remote = remoteParts[i] || 0;
    const current = currentParts[i] || 0;
    if (remote > current) return true;
    if (remote < current) return false;
  }
  return false;
};

// ============================ 服务器状态检查系统 ============================
/**
 * 检查服务器状态
 */
const checkServerStatus = async () => {
  log('正在检查服务器连接状态...');
  
  for (let attempt = 0; attempt <= 2; attempt++) {
    if (attempt > 0) {
      await delay(1000);
    }
    
    try {
      const resp = await httpFetch('https://zrcdy.dpdns.org/lx/status.php', {
        method: 'GET',
        timeout: 5000,
        headers: {
          'User-Agent': 'LX-Music-Mobile/星海音乐源',
          'Accept': 'application/json'
        }
      });
      
      if (resp.statusCode !== 200) {
        throw new Error(`HTTP状态码异常: ${resp.statusCode}`);
      }
      
      let apiData = resp.body;
      if (typeof apiData === 'string') {
        try {
          apiData = JSON.parse(apiData);
        } catch (parseError) {
          throw new Error(`JSON解析失败: ${parseError.message}`);
        }
      }
      
      if (!apiData || typeof apiData !== 'object') {
        throw new Error('服务器返回数据格式无效');
      }
      
      const isEnabled = apiData.enabled !== false;
      log(`服务器连接状态检查结果: ${isEnabled ? '服务正常' : '服务受限'}`);
      
      return {
        enabled: isEnabled,
        message: apiData.message || (isEnabled ? '服务正常' : '服务暂时不可用'),
        error: null
      };
      
    } catch (err) {
      log(`服务器连接检查失败(第${attempt + 1}次):`, err.message);
      
      if (attempt === 2) {
        log('服务器连接检查多次失败，尝试本地模式运行');
        return {
          enabled: true,
          message: `服务器连接失败，使用本地模式: ${err.message}`,
          error: err.message
        };
      }
    }
  }
  
  return {
    enabled: true,
    message: '服务器连接检查过程异常，使用本地模式',
    error: '未知错误'
  };
};

// ============================ 自动更新系统 ============================
const checkAutoUpdate = async () => {
  if (!musicSourceEnabled) return;
  
  try {
    const resp = await httpFetch(UPDATE_CONFIG.versionApiUrl, {
      timeout: 10000,
      headers: { 
        'Content-Type': 'application/json',
        'User-Agent': 'LX-Music-Mobile'
      }
    });

    if (resp.statusCode !== 200) return;

    let apiData = resp.body;
    if (typeof apiData === 'string') {
      try {
        apiData = JSON.parse(apiData.trim().replace(/^\uFEFF/, ''));
      } catch (e) {
        return;
      }
    }

    if (!apiData || typeof apiData !== 'object') return;

    const remoteVersion = apiData.version || apiData.VERSION || apiData.ver;
    if (!remoteVersion) return;

    const updateLog = apiData.changelog || apiData.changelog || '暂无更新日志';
    const minRequiredVersion = apiData.min_required || apiData.minRequired || 'v1.0.0';
    const updateUrl = apiData.update_url || apiData.updateUrl || UPDATE_CONFIG.latestScriptUrl;

    const needUpdate = compareVersions(remoteVersion, UPDATE_CONFIG.currentVersion);
    
    if (needUpdate) {
      log('发现新版本:', remoteVersion, '当前版本:', UPDATE_CONFIG.currentVersion);
      
      const isForceUpdate = compareVersions(remoteVersion, minRequiredVersion) && 
                           compareVersions(minRequiredVersion, UPDATE_CONFIG.currentVersion);
      
      const updateMessage = `【星海音乐源更新通知】\n当前版本：${UPDATE_CONFIG.currentVersion}\n最新版本：${remoteVersion}\n\n更新内容：\n${updateLog}${
        isForceUpdate ? '\n\n⚠️ 此版本需要强制更新，请立即更新以正常使用' : ''
      }`;

      send(EVENT_NAMES.updateAlert, {
        log: updateMessage,
        updateUrl: updateUrl,
        confirmText: '立即更新',
        cancelText: isForceUpdate ? '退出应用' : '暂不更新'
      });
    }
  } catch (err) {
    log('更新检查失败:', err.message);
  }
};

// ============================ 音频链接解析核心 ============================
/**
 * 使用主API(GD Studio)获取音频地址
 */
const getMusicUrlFromMainAPI = async (source, songId, apiQuality) => {
  const apiSource = MAIN_API_SOURCE_MAP[source];
  if (!apiSource) {
    throw new Error('当前平台不支持');
  }

  const requestUrl = `${MAIN_API_URL}&types=url&source=${apiSource}&id=${songId}&br=${apiQuality}`;

  const resp = await httpFetch(requestUrl, {
    method: 'GET',
    headers: {
      'User-Agent': 'LX-Music-Mobile',
      'Accept': 'application/json'
    }
  });

  const apiData = typeof resp.body === 'object' ? resp.body : JSON.parse(resp.body);
  if (!apiData.url) {
    throw new Error('音频解析失败');
  }

  return apiData.url;
};

/**
 * 使用备用API(TuneHub)获取音频地址
 */
const getMusicUrlFromBackupAPI = async (source, songId, actualQuality) => {
  const apiSource = BACKUP_API_SOURCE_MAP[source];
  if (!apiSource) {
    throw new Error('备用API不支持此平台');
  }

  const requestUrl = `${BACKUP_API_URL}?source=${apiSource}&id=${songId}&type=url&br=${actualQuality}`;

  try {
    // 备用API直接返回音频地址或重定向
    return requestUrl;
  } catch (error) {
    log('备用API请求异常:', error.message);
    throw new Error(`备用API请求失败：${error.message}`);
  }
};

/**
 * 获取音频播放地址核心方法
 */
const handleGetMusicUrl = async (source, musicInfo, quality) => {
  if (!musicSourceEnabled) {
    throw new Error('服务暂时不可用');
  }

  if (!serverCheckCompleted) {
    throw new Error('服务初始化中，请稍后');
  }

  logSimple('解析音频地址', source, musicInfo, '开始');

  const songId = musicInfo.hash ?? musicInfo.songmid ?? musicInfo.id;
  if (!songId) {
    throw new Error('歌曲信息不完整');
  }

  const availableQualities = MUSIC_QUALITY[source] || ['128k', '192k', '320k', 'flac'];
  const actualQuality = mapQuality(quality, availableQualities);
  
  if (actualQuality !== quality) {
    log(`音质自动映射: ${quality} -> ${actualQuality} (平台: ${source})`);
  }

  let finalUrl = null;
  let lastError = null;
  
  // 策略1：先尝试主API
  try {
    const mainApiQualityMap = {
      '128k': '128',
      '192k': '192',
      '320k': '320',
      'flac': '740',
      'flac24bit': '999'
    };
    
    const apiQuality = mainApiQualityMap[actualQuality] || '320';
    finalUrl = await getMusicUrlFromMainAPI(source, songId, apiQuality);
    logSimple('解析音频地址', source, musicInfo, '成功(主API)');
  } catch (error) {
    lastError = error;
    logSimple('解析音频地址', source, musicInfo, '主API失败', error.message);
    
    // 策略2：主API失败后尝试备用API
    if (BACKUP_API_SOURCE_MAP[source]) {
      try {
        finalUrl = await getMusicUrlFromBackupAPI(source, songId, actualQuality);
        logSimple('解析音频地址', source, musicInfo, '成功(备用API)');
        log('备用API返回的音频地址:', finalUrl);
      } catch (backupError) {
        lastError = backupError;
        logSimple('解析音频地址', source, musicInfo, '备用API失败', backupError.message);
      }
    } else {
      log(`平台 ${source} 不支持备用API，跳过备用尝试`);
    }
  }

  if (!finalUrl) {
    const errMsg = `无法获取音频地址：${lastError ? lastError.message : '未知错误'}`;
    logSimple('解析音频地址', source, musicInfo, '完全失败', errMsg);
    throw new Error(errMsg);
  }

  return finalUrl;
};

// ============================ 注册音乐平台 ============================
const musicSources = {};
MUSIC_SOURCE.forEach(sourceKey => {
  musicSources[sourceKey] = {
    name: {
      wy: '网易云音乐',
      tx: 'QQ音乐',
      kw: '酷我音乐',
      kg: '酷狗音乐',
      mg: '咪咕音乐'
    }[sourceKey],
    type: 'music',
    actions: ['musicUrl'],
    qualitys: MUSIC_QUALITY[sourceKey]
  };
});

/**
 * 注册事件监听器
 */
on(EVENT_NAMES.request, ({ action, source, info }) => {
  if (action !== 'musicUrl') {
    return Promise.reject(new Error('不支持的操作类型'));
  }

  if (!info || !info.musicInfo || !info.type) {
    return Promise.reject(new Error('请求参数不完整'));
  }

  return handleGetMusicUrl(source, info.musicInfo, info.type)
    .then(url => Promise.resolve(url))
    .catch(err => Promise.reject(err));
});

// ============================ 初始化入口 ============================
const initializeMusicSource = () => {
  log('========================================');
  log('星海音乐源 v2.2.7 初始化开始');
  log('========================================');
  log('主API: GD Studio API');
  log('备用API: TuneHub API (支持网易云、QQ、酷我)');
  log('支持的平台: 网易云、QQ、酷我、酷狗、咪咕');
  log('========================================');
  
  // 同步检查服务器状态，如果失败则直接抛出错误
  checkServerStatus().then(serverResult => {
    musicSourceEnabled = serverResult.enabled;
    serverCheckCompleted = true;
    
    if (!musicSourceEnabled) {
      log('⚠️ 服务器状态异常，服务受限');
      log('服务器返回信息:', serverResult.message);
      
      // 创建自定义错误对象并抛出，触发初始化失败弹窗
      const error = new Error(serverResult.message || '音乐服务已禁用，暂不提供访问');
      error.isServerRestricted = true;
      
      // 不发送inited事件，让初始化失败
      // 直接抛出错误，LX Music会捕获并显示初始化失败弹窗
      throw error;
    }
    
    log('✅ 服务器连接状态检查完成，服务已启用');
    
    // 发送初始化成功事件
    send(EVENT_NAMES.inited, {
      status: true,
      openDevTools: false,
      sources: musicSources,
      initStatus: 'ready'
    });
    
    log('========================================');
    log('星海音乐源初始化完成');
    log('========================================');
    
    // 延迟检查更新
    setTimeout(() => {
      checkAutoUpdate();
    }, 3000);
    
  }).catch(error => {
    if (error.isServerRestricted) {
      // 服务器限制错误，直接抛出，不处理
      throw error;
    }
    
    log('服务器连接检查失败，使用降级模式:', error.message);
    musicSourceEnabled = true;
    serverCheckCompleted = true;
    
    // 即使连接失败，也发送初始化成功，但使用降级模式
    send(EVENT_NAMES.inited, {
      status: true,
      openDevTools: false,
      sources: musicSources,
      initStatus: 'degraded'
    });
    
    log('星海音乐源初始化完成（降级模式）');
    
    setTimeout(() => {
      checkAutoUpdate();
    }, 3000);
  });
};

// 启动初始化
try {
  initializeMusicSource();
} catch (error) {
  // 这里会捕获同步错误，但initializeMusicSource中的异步错误会在Promise链中抛出
  // 对于同步错误，我们直接重新抛出
  if (error.isServerRestricted) {
    throw error;
  }
  log('初始化过程异常:', error);
}