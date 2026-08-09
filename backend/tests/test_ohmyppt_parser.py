from ppth5.backend.main import parse_json_pages, parse_sep, usable_pages


def test_parses_exact_separator_format() -> None:
    text = """SLIDE_TITLE: GPIO 输入模式
SLIDE_OUTLINE: 对比浮空、上拉和下拉输入
SLIDE_HTML: <section><h1>GPIO 输入模式</h1><p data-anim="fade-up">三种模式对比</p></section>
---
SLIDE_TITLE: GPIO 输出模式
SLIDE_OUTLINE: 对比推挽和开漏输出
SLIDE_HTML:
<section><h1>GPIO 输出模式</h1><p data-anim-trigger="click">推挽与开漏</p></section>"""

    pages = usable_pages(parse_sep(text))

    assert [page["title"] for page in pages] == ["GPIO 输入模式", "GPIO 输出模式"]
    assert "data-anim-trigger" in pages[1]["h"]


def test_parses_chinese_markdown_labels_and_html_fence() -> None:
    text = """### 幻灯片 1
**标题：** STM32 时钟使能
**大纲：** 从 RCC 到 GPIO 端口
**页面HTML：**
```html
<div class="clock-flow"><h1>先时钟，后配置</h1><ol><li>使能 RCC</li><li>初始化 GPIO</li></ol></div>
```
"""

    pages = usable_pages(parse_sep(text))

    assert len(pages) == 1
    assert pages[0]["title"] == "STM32 时钟使能"
    assert "clock-flow" in pages[0]["h"]


def test_parses_json_wrapped_in_markdown() -> None:
    text = """```json
{"slides":[{"title":"中断优先级","contentOutline":"NVIC 抢占与响应优先级","html":"<main><h1>NVIC</h1><p>先比较抢占优先级，再比较响应优先级。</p></main>"}]}
```"""

    pages = usable_pages(parse_json_pages(text))

    assert len(pages) == 1
    assert pages[0]["title"] == "中断优先级"


def test_rejects_empty_or_plain_text_slide_body() -> None:
    pages = usable_pages([
        {"title": "空页面", "contentOutline": "", "h": ""},
        {"title": "纯文本", "contentOutline": "", "h": "这不是 HTML 页面内容，不能作为幻灯片成功返回。"},
    ])

    assert pages == []
