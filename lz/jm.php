<?php
/**
 * 交互式M3U代理网关
 * 部署在Termux，通过浏览器交互配置。
 * 用法: php -S 0.0.0.0:8080 proxy.php
 */

// 默认参数
$DEFAULT_HOST = "zz.zoho.to";
$DEFAULT_PATH = "/i/";
$DEFAULT_PARAM = "T";
$DEFAULT_VALUE = "m3u";
$USER_AGENT = "okhttp/5.0.0-alpha.14"; // 可选: 'okhttp/3.12.11'

// 获取GET参数，用于动态配置
$host = $_GET['h'] ?? $DEFAULT_HOST;
$path = $_GET['p'] ?? $DEFAULT_PATH;
$param = $_GET['k'] ?? $DEFAULT_PARAM;
$value = $_GET['v'] ?? $DEFAULT_VALUE;

// 构建目标URL
$targetUrl = "http://" . $host . $path . '?' . http_build_query([$param => $value]);

// 如果没有GET参数，显示配置页面
if (empty($_GET)) {
    ?>
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>📡 M3U代理配置</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Segoe UI', sans-serif; background: #f5f7fa; }
            .container { max-width: 800px; margin: 20px auto; padding: 20px; }
            .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; margin-bottom: 20px; text-align: center; }
            .form-group { margin-bottom: 18px; }
            label { display: block; margin-bottom: 6px; font-weight: 600; color: #34495e; }
            input[type="text"] { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; }
            button { background: #3498db; color: white; padding: 14px 20px; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; width: 100%; }
            button:hover { background: #2980b9; }
            .info { margin-top: 20px; padding: 15px; background: #e8f4fd; border-radius: 6px; font-size: 14px; color: #2980b9; }
            .current { word-break: break-all; padding: 10px; background: #f8f9fa; border: 1px solid #ddd; border-radius: 4px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>📡 M3U代理配置</h1>
                <form method="GET">
                    <div class="form-group">
                        <label for="h">主机 (Host)</label>
                        <input type="text" id="h" name="h" value="<?= htmlspecialchars($DEFAULT_HOST) ?>" required />
                    </div>
                    <div class="form-group">
                        <label for="p">路径 (Path)</label>
                        <input type="text" id="p" name="p" value="<?= htmlspecialchars($DEFAULT_PATH) ?>" required />
                    </div>
                    <div class="form-group">
                        <label for="k">参数名 (Key)</label>
                        <input type="text" id="k" name="k" value="<?= htmlspecialchars($DEFAULT_PARAM) ?>" required />
                    </div>
                    <div class="form-group">
                        <label for="v">参数值 (Value)</label>
                        <input type="text" id="v" name="v" value="<?= htmlspecialchars($DEFAULT_VALUE) ?>" required />
                    </div>
                    <button type="submit">生成并获取M3U</button>
                </form>

                <?php if (!empty($_GET)): ?>
                    <div>
                        <p><strong>请求已发送至:</strong></p>
                        <div class="current"><?= htmlspecialchars($targetUrl) ?></div>
                        <p>✅ 请等待，M3U内容将在下方加载或由播放器自动处理。</p>
                    </div>
                <?php endif; ?>

                <div class="info">
                    <p><strong>说明:</strong></p>
                    <p>• 本页面在您的手机上运行，利用手机的网络环境获取被保护的M3U源。</p>
                    <p>• 您可以将此页面的链接分享给局域网内的设备。</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    <?php
    exit;
}

// 当有参数时，作为代理，获取并返回M3U内容
function fetch($url, $ua) {
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_USERAGENT      => $ua,
        CURLOPT_HTTPHEADER     => ['Accept: */*'],
        CURLOPT_ENCODING       => 'gzip',
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
    ]);
    $content = curl_exec($ch);
    curl_close($ch);
    return $content ?: "#EXTM3U\n#EXTINF:-1,Fetch Error\nhttp://127.0.0.1/error";
}

// 设置为M3U内容类型
header('Content-Type: application/x-mpegurl; charset=UTF-8');
echo fetch($targetUrl, $USER_AGENT);
?>