from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--window-size=1280,800')

driver = webdriver.Chrome(options=options)

try:
    print("Navigating to app...")
    driver.get("http://localhost:8502")
    
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//h2[contains(., \"Today's Outdoor Quest\")]"))
    )
    print("App loaded. Uploading file...")
    file_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
    )
    
    # Send absolute path to the file input
    clip_path = os.path.abspath(r"samples\Brahminy Starling - Sturnia pagodarum.mp3")
    file_input.send_keys(clip_path)
    
    print("Waiting for loader...")
    # Wait for the loader to appear
    WebDriverWait(driver, 120).until(
        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Writing your field card...')]"))
    )
    print("Loader appeared!")
    
    start_time = time.time()
    
    for delay in [1, 4, 8]:
        now = time.time()
        elapsed = now - start_time
        if elapsed < delay:
            time.sleep(delay - elapsed)
            
        print(f"--- AT {delay}s ---")
        
        # Check containers
        containers = driver.find_elements(By.XPATH, "//*[@data-testid='stElementContainer']")
        for i, c in enumerate(containers[:5]): # just check a few
            is_stale = c.get_attribute('data-stale')
            opacity = c.value_of_css_property('opacity')
            text = c.text[:20].replace('\n', ' ')
            if is_stale == 'true':
                print(f"Container '{text}' is stale! opacity: {opacity}")
        
        # Take screenshot
        driver.save_screenshot(f"gemma_{delay}s.png")
        print(f"Saved gemma_{delay}s.png")

finally:
    driver.quit()
