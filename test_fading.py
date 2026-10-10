import asyncio
from playwright.async_api import async_playwright
import time
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        print("Navigating to app...")
        await page.goto("http://localhost:8502")
        await page.wait_for_selector("text=Today's Outdoor Quest")
        
        print("Checking Test mode...")
        # Check Advanced expander
        advanced_expander = page.locator("text=Advanced")
        if await advanced_expander.count() > 0:
            await advanced_expander.click()
            await page.wait_for_selector("text=Load a sample walk")
            
        print("Clicking Load a sample walk...")
        await page.locator("text=Load a sample walk").click()
        
        print("Waiting for 'Writing your field card...'")
        # Wait for the loader to appear
        loader = page.locator("text=Writing your field card...")
        await loader.wait_for(state="visible", timeout=60000)
        print("Loader appeared!")
        
        # Take screenshots at 1s, 4s, 8s
        for delay in [1, 4, 8]:
            await asyncio.sleep(delay - (1 if delay > 1 else 0)) # roughly correct
            print(f"--- AT {delay}s ---")
            
            # Find the main container holding the results
            # Results start with "File Analysis" panel
            file_analysis = page.locator("text=File Analysis")
            if await file_analysis.count() > 0:
                parent = file_analysis.locator("..")
                is_stale = await parent.evaluate("el => el.getAttribute('data-stale')")
                opacity = await parent.evaluate("el => window.getComputedStyle(el).opacity")
                print(f"File Analysis container - data-stale: {is_stale}, opacity: {opacity}")
            
            # Check a bingo element
            quest_tiles = page.locator("text=Today's Quest Tiles")
            if await quest_tiles.count() > 0:
                parent = quest_tiles.locator("..")
                is_stale = await parent.evaluate("el => el.getAttribute('data-stale')")
                opacity = await parent.evaluate("el => window.getComputedStyle(el).opacity")
                print(f"Quest Tiles container - data-stale: {is_stale}, opacity: {opacity}")
            
            await page.screenshot(path=f"screenshot_{delay}s.png")
            print(f"Saved screenshot_{delay}s.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
