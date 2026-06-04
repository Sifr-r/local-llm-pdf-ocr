import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # Go to local server
        await page.goto("http://localhost:8000")
        await page.wait_for_timeout(2000)
        
        # Upload a test document
        file_path = os.path.join("examples", "dense.pdf")
        if os.path.exists(file_path):
            await page.set_input_files('input#file-input', file_path)
            
            await page.wait_for_timeout(1000)
            await page.click('button#start-btn')
            print("Started OCR, waiting for it to finish...")
            await page.wait_for_function('document.getElementById("process-view").classList.contains("hidden")', timeout=180000)
            await page.wait_for_timeout(1000)
        else:
            print("dense.pdf not found, just taking empty screenshot.")
            
        # Take screenshot
        screenshot_path = "C:\\Users\\rahin\\.gemini\\antigravity\\brain\\744a3706-987c-4902-b0e3-244629f68fdb\\scratch\\screenshot.png"
        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
        await page.screenshot(path=screenshot_path)
        print("Screenshot saved to", screenshot_path)
        
        await browser.close()

asyncio.run(run())
