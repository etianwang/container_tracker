from playwright.sync_api import sync_playwright


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    context.grant_permissions(['clipboard-read', 'clipboard-write'], origin='http://127.0.0.1:8080')
    page = context.new_page()
    page.goto('http://127.0.0.1:8080/', wait_until='networkidle')
    assert {'hapag', 'one', 'zim'} <= set(page.locator('#carrier option').evaluate_all('(options) => options.map(option => option.value)'))
    page.evaluate("navigator.clipboard.writeText('CAAU6205115')")
    page.locator('h1').click()
    page.keyboard.press('Control+V')
    page.wait_for_function("document.querySelector('#container').value === 'CAAU6205115'")
    page.locator('h1').click()
    page.keyboard.press('Control+A')
    page.wait_for_function("(() => { const input = document.querySelector('#container'); return input.selectionStart === 0 && input.selectionEnd === input.value.length })()")
    page.locator('#track').click()
    page.wait_for_function("document.querySelector('main').innerText.includes('卸船')")
    assert '南沙新港' in page.locator('main').inner_text()
    page.locator('#container').fill('OOCU9568230')
    page.locator('#carrier').select_option('auto')
    with page.expect_popup() as popup_info:
        page.locator('#track').click()
    popup = popup_info.value
    page.wait_for_function("document.querySelector('main').innerText.includes('官方查询页已在新窗口打开')")
    popup.close()
    browser.close()
    print('ok')
