import os
import sys
import re
import time
import asyncio
import subprocess

PW_BROWSERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pw-browsers")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PW_BROWSERS_DIR

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from profile_manager import get_profile_cookies
from data_manager import log_activation_detail

def ensure_chromium_installed():
    try:
        print(f"Downloading Chromium binary into {PW_BROWSERS_DIR}...")
        os.makedirs(PW_BROWSERS_DIR, exist_ok=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    except Exception as e:
        print(f"Error installing Chromium: {e}")

async def run_activation_attempt(email: str, clean_code: str, cookies: list, mobile: str = ""):
    steps = []
    start_time = time.time()
    
    def log_step(msg: str):
        elapsed = round(time.time() - start_time, 2)
        steps.append(f"[{elapsed}s] {msg}")

    log_step(f"Starting Dreamstar TV Engine for {email} with code {clean_code}")

    async with async_playwright() as p:
        browser = None
        try:
            launch_args = [
                "--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage", "--disable-gpu", "--no-first-run", "--no-zygote",
                "--single-process", "--disable-extensions"
            ]
            
            try:
                browser = await p.chromium.launch(headless=True, args=launch_args)
            except Exception as launch_err:
                if "Executable doesn't exist" in str(launch_err) or "playwright install" in str(launch_err):
                    log_step("Chromium executable missing. Triggering binary download...")
                    ensure_chromium_installed()
                    browser = await p.chromium.launch(headless=True, args=launch_args)
                else:
                    raise launch_err

            log_step("Browser core initialized successfully.")

            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )

            formatted_cookies = []
            for c in cookies:
                cookie_dict = {
                    "name": c.get("name"),
                    "value": c.get("value"),
                    "domain": c.get("domain", ".netflix.com"),
                    "path": c.get("path", "/")
                }
                if "sameSite" in c and c["sameSite"] in ["Strict", "Lax", "None"]:
                    cookie_dict["sameSite"] = c["sameSite"]
                formatted_cookies.append(cookie_dict)

            await context.add_cookies(formatted_cookies)
            log_step(f"Loaded {len(formatted_cookies)} session cookies into memory.")

            page = await context.new_page()

            # 1. Pre-flight session check
            log_step("Running session validation via netflix.com/youraccount...")
            try:
                await page.goto("https://www.netflix.com/youraccount", wait_until="domcontentloaded", timeout=14000)
            except PlaywrightTimeoutError:
                await page.goto("https://www.netflix.com/youraccount", wait_until="commit", timeout=9000)

            await page.wait_for_timeout(1200)
            acc_url = page.url
            log_step(f"Account check endpoint: {acc_url}")

            is_login = (
                "login" in acc_url 
                or "signin" in acc_url 
                or await page.locator("text='Enter your info to sign in'").count() > 0
                or await page.locator("input[name='userLoginId'], input[autocomplete='email']").count() > 0
            )

            if is_login:
                log_step("Detected login challenge. Session cookies are expired.")
                await browser.close()
                err_msg = "Cookies expired. Please contact Dreamstar admin to update credentials."
                log_activation_detail(mobile, email, clean_code, False, err_msg, steps)
                return {"success": False, "error_code": "COOKIES_EXPIRED", "message": err_msg}

            log_step("Session authenticated. Moving to tv2 activation portal...")

            # 2. Open TV2 activation
            try:
                await page.goto("https://www.netflix.com/tv2", wait_until="domcontentloaded", timeout=16000)
            except PlaywrightTimeoutError:
                await page.goto("https://www.netflix.com/tv2", wait_until="commit", timeout=8000)

            await page.wait_for_timeout(1200)
            current_url = page.url
            log_step(f"Portal URL: {current_url}")

            # 3. Dynamic UI detection
            split_inputs = page.locator("input.pin-number-input, input[data-uia^='pin-number-']")
            single_input = page.locator("input[name='rendezvousCode'], input[autocomplete='one-time-code']").first
            
            ui_type = None
            for _ in range(6):
                if await split_inputs.count() >= 8:
                    ui_type = "WHITE_UI_SPLIT"
                    break
                elif await single_input.count() > 0:
                    ui_type = "BLACK_UI_SINGLE"
                    break
                await page.wait_for_timeout(800)

            log_step(f"Detected UI variant: {ui_type or 'UNKNOWN'}")

            if not ui_type:
                await browser.close()
                err_msg = "Activation fields not detected on netflix.com/tv2."
                log_activation_detail(mobile, email, clean_code, False, err_msg, steps)
                return {"success": False, "error_code": "INPUT_NOT_FOUND", "message": err_msg}

            # 4. Input dispatch
            if ui_type == "WHITE_UI_SPLIT":
                log_step("Filling 8 split PIN boxes with physical keystrokes...")
                first_box = split_inputs.first
                await first_box.click()
                await page.wait_for_timeout(100)
                
                for digit in clean_code:
                    await page.keyboard.press(digit)
                    await page.wait_for_timeout(85)

                entered_chars = []
                for i in range(8):
                    b = split_inputs.nth(i)
                    val = await b.input_value()
                    entered_chars.append(val)
                    if val != clean_code[i]:
                        await b.click()
                        await b.fill(clean_code[i])
                
                log_step(f"Verified split PIN: {''.join(entered_chars)}")

            elif ui_type == "BLACK_UI_SINGLE":
                log_step("Filling single React input field...")
                await single_input.click()
                await page.wait_for_timeout(150)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.wait_for_timeout(80)
                
                for digit in clean_code:
                    await page.keyboard.press(digit)
                    await page.wait_for_timeout(85)

                await single_input.dispatch_event("input")
                await single_input.dispatch_event("change")
                log_step(f"Verified single input: '{await single_input.input_value()}'")

            await page.wait_for_timeout(500)

            # 5. Single-click submission (Double-submission safe)
            submit_selectors = [
                "button[data-uia='witcher-code-submit']",
                "button.tvsignup-continue-button",
                "button[data-uia='continue-button']",
                "button:has-text('Enter Code to Continue')",
                "button:has-text('Continue')",
                "button[type='submit']"
            ]
            
            clicked = False
            for selector in submit_selectors:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    log_step(f"Clicking activation button: {selector}")
                    await btn.click(force=True)
                    clicked = True
                    break
            
            if not clicked:
                log_step("Selector not found. Pressing Enter as fallback...")
                await page.keyboard.press("Enter")

            # 6. Verification polling
            log_step("Waiting for Netflix server activation handshake...")
            for poll_sec in range(15):
                await page.wait_for_timeout(1000)
                
                if page.url != current_url:
                    log_step(f"[T+{poll_sec}s] URL redirect to: {page.url}")
                    current_url = page.url

                # Profile selection screen handler
                profile_items = page.locator("[data-uia='action-select-profile'], .profile-link, .profile-icon, [data-uia^='profile-']")
                if await profile_items.count() > 0 and await profile_items.first.is_visible():
                    log_step("Profile selection detected. Auto-selecting primary profile...")
                    try:
                        await profile_items.first.click(timeout=3000)
                        await page.wait_for_timeout(2000)
                    except Exception:
                        pass
                    await browser.close()
                    log_activation_detail(mobile, email, clean_code, True, "Activation complete (Profile confirmed)", steps)
                    return {"success": True, "message": "netflix activated"}

                # Redirect away from tv2
                if "/tv2" not in page.url:
                    log_step("URL changed away from activation endpoint. Confirmed!")
                    await browser.close()
                    log_activation_detail(mobile, email, clean_code, True, "Activation complete (URL Redirected)", steps)
                    return {"success": True, "message": "netflix activated"}

                # Explicit success prompts
                success_text = page.locator("text='connected', text='Connected', text='Ready to watch', text='Start Watching', text='All set', text='All Set', text='signed in', text='Signed In', text='Return to your TV'")
                if await success_text.count() > 0 and await success_text.first.is_visible():
                    log_step("Success banner detected on screen.")
                    await browser.close()
                    log_activation_detail(mobile, email, clean_code, True, "Activation complete (Screen confirmed)", steps)
                    return {"success": True, "message": "netflix activated"}

                # Error banner
                error_locators = page.locator(
                    "[data-uia='witcher-code-input-error'], "
                    "[data-hcw-form-control-validation='true'], "
                    "[data-uia*='error'], "
                    ".ui-message-error, .ui-message-contents, .error-box"
                )
                if await error_locators.count() > 0:
                    for idx in range(await error_locators.count()):
                        el = error_locators.nth(idx)
                        if await el.is_visible():
                            err_text = (await el.inner_text()).strip()
                            if err_text and len(err_text) > 3:
                                log_step(f"Netflix error response: '{err_text}'")
                                await browser.close()
                                log_activation_detail(mobile, email, clean_code, False, err_text, steps)
                                return {"success": False, "error_code": "ACTIVATION_FAILED", "message": err_text}

            log_step("Verification polling exceeded without state change. TV code likely invalid/expired.")
            await browser.close()
            err_msg = "Invalid or expired TV code. Please check your TV screen."
            log_activation_detail(mobile, email, clean_code, False, err_msg, steps)
            return {"success": False, "error_code": "ACTIVATION_FAILED", "message": err_msg}

        except Exception as e:
            log_step(f"Execution exception: {str(e)}")
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            log_activation_detail(mobile, email, clean_code, False, f"Automation exception: {str(e)}", steps)
            raise e

async def activate_tv(email: str, raw_code: str, mobile: str = "", expiry_date: str = ""):
    clean_code = re.sub(r'[^a-zA-Z0-9]', '', raw_code).upper()
    if len(clean_code) != 8:
        return {
            "success": False,
            "error_code": "INVALID_CODE_FORMAT",
            "message": f"TV code must be exactly 8 characters. Received: {raw_code}",
            "formatted_output": "Invalid TV code format."
        }

    cookies = get_profile_cookies(email)
    if not cookies or len(cookies) == 0:
        msg = "Cookies expired. Please contact Dreamstar admin."
        log_activation_detail(mobile, email, clean_code, False, msg, ["No cookies stored for this profile."])
        return {"success": False, "error_code": "COOKIES_EXPIRED", "message": msg, "formatted_output": msg}

    try:
        res = await run_activation_attempt(email=email, clean_code=clean_code, cookies=cookies, mobile=mobile)
        if res.get("error_code") == "COOKIES_EXPIRED":
            msg = "Cookies expired. Please contact Dreamstar admin."
            res["message"] = msg
            res["formatted_output"] = msg
            return res

        if res.get("success"):
            user_mobile_str = str(mobile).strip() if mobile else "N/A"
            expiry_str = str(expiry_date).strip() if expiry_date else "Active"
            
            # Clean Dreamstar output format (code fetcher removed)
            formatted_output = (
                f"🌟 DREAMSTAR SOLUTIONS - TV ACTIVATION SUCCESSFUL\n"
                f"═════════════════════════════════════════════════\n"
                f"📱 User Mobile : {user_mobile_str}\n"
                f"📧 Profile     : {email}\n"
                f"📅 Expiry Date : {expiry_str}\n"
                f"🔑 Code Used   : {clean_code}\n"
                f"═════════════════════════════════════════════════\n"
                f"✅ Your TV is now logged in. Enjoy your streaming!\n"
                f"💬 WhatsApp Support: +91 99914 83279"
            )
            res["formatted_output"] = formatted_output
            res["email"] = email
            res["code"] = clean_code
        else:
            res["formatted_output"] = res.get("message", "Activation failed.")
        return res
    except Exception as e:
        msg = f"Automation error: {str(e)}"
        return {"success": False, "error_code": "EXECUTION_ERROR", "message": msg, "formatted_output": msg}
