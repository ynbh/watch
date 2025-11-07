

"""
Launch a Selenium Browser Session to embed the iframe for the media, with only the iframe. 
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import tempfile
from pathlib import Path
import html
import time

IFRAME_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>VidKing Player</title>
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            background: #000;
            height: 100%;
            overflow: hidden;
        }}
        iframe {{
            border: none;
            width: 100vw;
            height: 100vh;
        }}
    </style>
</head>
<body>
    <iframe
        id="media-frame"
        src="{src}"
        sandbox="allow-scripts allow-same-origin"
        allow="autoplay; fullscreen; picture-in-picture"
        allowfullscreen
        referrerpolicy="no-referrer"
    ></iframe>
    <script>
        const frame = document.getElementById("media-frame");
        frame.addEventListener("load", () => {{
            const sandboxValue = frame.getAttribute("sandbox");
            // brief window without sandbox attribute can defeat naive detectors
            frame.removeAttribute("sandbox");
            requestAnimationFrame(() => {{
                frame.setAttribute("sandbox", sandboxValue);
            }});
        }});
    </script>
</body>
</html>
"""


def _write_iframe_wrapper(url: str) -> Path:
    safe_url = html.escape(url, quote=True)
    html_doc = IFRAME_TEMPLATE.format(src=safe_url)
    tmp_file = tempfile.NamedTemporaryFile("w", delete=False, suffix=".html")
    with tmp_file as handle:
        handle.write(html_doc)
    return Path(tmp_file.name)


def launch_media(URL):
    opts = Options()
    wrapper_path = _write_iframe_wrapper(URL)
    opts.add_argument(f"--app={wrapper_path.as_uri()}")  # chromeless window
    opts.add_argument("--window-size=960,540")
    opts.add_argument("--window-position=200,120")
    opts.add_argument("--disable-infobars")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=opts)
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                """
            },
        )
    except Exception:
        pass

    driver.get(wrapper_path.as_uri())
    try:
        while True:
            try:
                # poll window handles; when user closes, this becomes empty/throws
                handles = driver.window_handles
            except Exception:
                break
            if not handles:
                break
            time.sleep(0.5)
    finally:
        # now we clean up because the user closed it
        try:
            driver.quit()
        except Exception:
            pass
        try:
            wrapper_path.unlink(missing_ok=True)
        except Exception:
            pass
