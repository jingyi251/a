<?php
/**
 * Jable TV M3U 播放列表生成器 - 随机5个视频
 * 用法：访问 http://127.0.0.1:8901/jable.php
 */

class JableSpider {
    private $siteUrl = "https://jable.tv";
    private $userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
    
    private function fetch($url) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
        curl_setopt($ch, CURLOPT_TIMEOUT, 30);
        curl_setopt($ch, CURLOPT_USERAGENT, $this->userAgent);
        curl_setopt($ch, CURLOPT_REFERER, $this->siteUrl . "/");
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        return ($httpCode == 200) ? $response : null;
    }
    
    /**
     * 从页面获取所有视频链接
     */
    private function getAllVideoLinks($url) {
        $videos = [];
        $html = $this->fetch($url);
        
        if (!$html) return $videos;
        
        // 提取所有视频链接
        $pattern = '/<a[^>]*href="([^"]*videos\/[^"]+)"[^>]*>/i';
        preg_match_all($pattern, $html, $matches);
        
        foreach ($matches[1] as $link) {
            if (strpos($link, 'http') !== 0) {
                $link = $this->siteUrl . '/' . ltrim($link, '/');
            }
            
            // 提取标题
            $title = '';
            // 尝试从链接中提取标题
            if (preg_match('/videos\/([^\/]+)/', $link, $titleMatch)) {
                $title = str_replace('-', ' ', $titleMatch[1]);
            }
            
            if (empty($title)) {
                $title = basename($link);
            }
            
            $videos[] = [
                'url' => $link,
                'title' => $title
            ];
        }
        
        return $videos;
    }
    
    /**
     * 获取视频真实m3u8地址
     */
    private function getM3u8Url($videoUrl) {
        $html = $this->fetch($videoUrl);
        if (!$html) return null;
        
        // 匹配m3u8地址
        $patterns = [
            '/https?:\/\/[^\s\'"<>]+\.m3u8[^\s\'"<>]*/i',
            '/source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']/i',
            '/file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']/i',
            '/url:\s*["\']([^"\']+\.m3u8[^"\']*)["\']/i'
        ];
        
        foreach ($patterns as $pattern) {
            if (preg_match($pattern, $html, $match)) {
                return $match[0];
            }
        }
        
        return null;
    }
    
    /**
     * 生成随机M3U播放列表
     */
    public function generateRandomM3U($count = 5) {
        $allVideos = [];
        
        // 多个来源，增加随机性
        $sources = [
            $this->siteUrl . '/latest-updates/',
            $this->siteUrl . '/hot/',
            $this->siteUrl . '/categories/chinese-subtitle/',
            $this->siteUrl . '/categories/uncensored/',
            $this->siteUrl . '/categories/hd/',
            $this->siteUrl . '/categories/exclusive/',
            $this->siteUrl . '/categories/creampie/',
            $this->siteUrl . '/categories/lesbian/'
        ];
        
        // 随机打乱来源顺序
        shuffle($sources);
        
        // 从每个来源获取视频，直到收集够为止
        foreach ($sources as $source) {
            if (count($allVideos) >= $count * 3) break; // 多收集一些用于随机选择
            
            $videos = $this->getAllVideoLinks($source);
            $allVideos = array_merge($allVideos, $videos);
            usleep(300000); // 延时0.3秒
        }
        
        // 去重
        $uniqueVideos = [];
        $seenUrls = [];
        foreach ($allVideos as $video) {
            if (!in_array($video['url'], $seenUrls)) {
                $seenUrls[] = $video['url'];
                $uniqueVideos[] = $video;
            }
        }
        
        // 随机打乱所有视频
        shuffle($uniqueVideos);
        
        // 取前N个
        $randomVideos = array_slice($uniqueVideos, 0, $count);
        
        // 输出M3U头
        header('Content-Type: application/x-mpegURL');
        header('Content-Disposition: attachment; filename="jable_random.m3u"');
        echo "#EXTM3U\n";
        echo "# 随机播放列表\n";
        echo "# 生成时间: " . date('Y-m-d H:i:s') . "\n";
        echo "# 随机种子: " . rand() . "\n\n";
        
        $success = 0;
        foreach ($randomVideos as $video) {
            echo "\n#EXTINF:-1, " . $video['title'] . "\n";
            
            $m3u8Url = $this->getM3u8Url($video['url']);
            if ($m3u8Url) {
                echo $m3u8Url . "\n";
                $success++;
            } else {
                // 如果获取不到m3u8，输出原始链接
                echo $video['url'] . "\n";
            }
            
            usleep(200000); // 延时0.2秒
        }
        
        echo "\n# 成功获取 " . $success . "/" . count($randomVideos) . " 个视频流\n";
    }
    
    /**
     * 极速随机模式 - 不解析m3u8，直接输出页面链接
     */
    public function generateQuickRandomM3U($count = 5) {
        $allVideos = [];
        
        // 从首页获取所有视频链接
        $html = $this->fetch($this->siteUrl);
        if ($html) {
            $pattern = '/<a[^>]*href="([^"]*videos\/[^"]+)"[^>]*>/i';
            preg_match_all($pattern, $html, $matches);
            
            foreach ($matches[1] as $link) {
                if (strpos($link, 'http') !== 0) {
                    $link = $this->siteUrl . '/' . ltrim($link, '/');
                }
                
                $title = '';
                if (preg_match('/videos\/([^\/]+)/', $link, $titleMatch)) {
                    $title = str_replace('-', ' ', $titleMatch[1]);
                }
                
                $allVideos[] = [
                    'url' => $link,
                    'title' => $title
                ];
            }
        }
        
        // 去重并随机
        $uniqueVideos = [];
        $seenUrls = [];
        foreach ($allVideos as $video) {
            if (!in_array($video['url'], $seenUrls)) {
                $seenUrls[] = $video['url'];
                $uniqueVideos[] = $video;
            }
        }
        
        shuffle($uniqueVideos);
        $randomVideos = array_slice($uniqueVideos, 0, $count);
        
        header('Content-Type: application/x-mpegURL');
        header('Content-Disposition: attachment; filename="jable_random_quick.m3u"');
        echo "#EXTM3U\n";
        echo "# 随机播放列表 (快速模式)\n";
        echo "# 生成时间: " . date('Y-m-d H:i:s') . "\n\n";
        
        foreach ($randomVideos as $video) {
            echo "\n#EXTINF:-1, " . $video['title'] . "\n";
            echo $video['url'] . "\n";
        }
        
        echo "\n# 共 " . count($randomVideos) . " 个视频\n";
        echo "# 提示: 此列表为页面链接，需要配合支持Jable解析的播放器使用\n";
    }
}

// 运行
$spider = new JableSpider();

$mode = isset($_GET['mode']) ? $_GET['mode'] : 'full';
$count = isset($_GET['count']) ? min(intval($_GET['count']), 20) : 5;

if ($mode == 'quick') {
    $spider->generateQuickRandomM3U($count);
} else {
    $spider->generateRandomM3U($count);
}
?>