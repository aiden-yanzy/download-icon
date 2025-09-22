import os
import requests
from urllib.parse import urlparse


def download_icon_from_google(domain, save_dir='icons', size=64):
    """
    使用 Google 的 favicon 服务下载网站图标。

    :param domain: 网站域名 (例如: "github.com")。
    :param save_dir: 保存图标的目录。
    :param size: 想要的图标尺寸 (例如: 16, 32, 64, 128)。
    :return: 如果下载成功，返回保存的文件路径；否则返回 None。
    """
    print(f"\n🚀 使用 Google 服务获取 '{domain}' 的图标...")

    # 确保保存目录存在
    os.makedirs(save_dir, exist_ok=True)

    # 构建 Google favicon 服务的 URL
    # 新版 t0.gstatic.com 接口更稳定，且支持 https:// 前缀
    full_url_for_api = f"https://{domain}" if not domain.startswith('http') else domain
    icon_url = f"https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url={full_url_for_api}&size={size}"

    try:
        response = requests.get(icon_url, timeout=10)

        # 检查请求是否成功
        if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
            # 从 Content-Type 推断文件扩展名
            content_type = response.headers['Content-Type']
            if 'svg' in content_type:
                ext = '.svg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'jpeg' in content_type:
                ext = '.jpg'
            else:
                ext = '.ico'

            # 清理域名作为文件名 (例如 "https://www.douban.com" -> "www.douban.com")
            clean_domain = urlparse(full_url_for_api).netloc
            filename = f"{clean_domain}_{size}x{size}{ext}"
            save_path = os.path.join(save_dir, filename)

            # 以二进制写模式保存文件
            with open(save_path, 'wb') as f:
                f.write(response.content)

            print(f"✅ 图标下载成功: {icon_url}")
            print(f"   保存至: {save_path}")
            return save_path
        else:
            print(f"❌ 下载失败 (状态码: {response.status_code})。Google 服务可能未找到该网站的图标。")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ 下载时发生网络错误: {e}")
        return None


# --- 使用示例 ---
if __name__ == "__main__":
    # 只需要提供域名即可
    # download_icon_from_google("github.com", size=128)
    #
    # download_icon_from_google("www.douban.com", size=128)

    download_icon_from_google("linux.do", size=128)

    # 即使是带有路径的 URL，它也能正确处理
    # download_icon_from_google("https://developer.mozilla.org/en-US/docs/Web/API", size=128)
