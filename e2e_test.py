"""
End-to-end test for the VisionAI Django app (TESTS 1-9 from the requirements).
Run with the Django dev server already live at http://127.0.0.1:8000/
Requires: pip install playwright && python -m playwright install chromium
"""
import sys
import time
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://127.0.0.1:8000"
STAMP = str(int(time.time()))
USER_A = {"name": f"Test User {STAMP}", "email": f"user{STAMP}@example.com", "pw": "StrongPass123!"}
USER_B = {"name": f"Second User {STAMP}", "email": f"second{STAMP}@example.com", "pw": "AnotherPass456!"}

results = []

def check(test_num, label, fn):
    try:
        fn()
        results.append((test_num, label, "PASS"))
        print(f"TEST {test_num}: {label} -> PASS")
    except Exception as exc:
        results.append((test_num, label, f"FAIL: {exc}"))
        print(f"TEST {test_num}: {label} -> FAIL: {exc}")

def register(page, name, email, pw):
    page.goto(f"{BASE_URL}/login/")
    page.get_by_placeholder("Full Name").fill(name)
    page.get_by_placeholder("Email").fill(email)
    page.get_by_placeholder("Password", exact=True).fill(pw)
    page.get_by_placeholder("Confirm Password").fill(pw)
    page.get_by_role("button", name="Sign Up").click()
    page.wait_for_url(f"{BASE_URL}/", timeout=10000)

def login(page, email, pw):
    page.goto(f"{BASE_URL}/login/")
    page.get_by_placeholder("Email").fill(email)
    page.get_by_placeholder("Password", exact=True).fill(pw)
    page.get_by_role("button", name="Login").click()
    page.wait_for_url(f"{BASE_URL}/", timeout=10000)

def logout(page):
    page.goto(f"{BASE_URL}/settings/")
    page.get_by_role("button", name="Logout").click()
    page.wait_for_url(f"{BASE_URL}/login/", timeout=10000)

def upload_image(page, path):
    page.goto(f"{BASE_URL}/")
    page.set_input_files('input[type="file"]', path)
    page.wait_for_selector(".result-card, #result-container .result", timeout=30000)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx_a = browser.new_context()
    page_a = ctx_a.new_page()
    ctx_b = browser.new_context()
    page_b = ctx_b.new_page()

    # Make a tiny valid PNG for upload testing
    import struct, zlib
    def make_png(path, w=64, h=64, color=(200, 30, 30)):
        def chunk(tag, data):
            c = struct.pack(">I", len(data)) + tag + data
            return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        raw = b""
        for _ in range(h):
            raw += b"\x00" + bytes(color) * w
        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(raw))
               + chunk(b"IEND", b""))
        with open(path, "wb") as f:
            f.write(png)

    img1 = f"test_img_{STAMP}_1.png"
    img2 = f"test_img_{STAMP}_2.png"
    make_png(img1)
    make_png(img2, color=(30, 30, 200))

    # TEST 1: Register -> auto-login -> dashboard -> recognize an image (real model)
    def test1():
        register(page_a, USER_A["name"], USER_A["email"], USER_A["pw"])
        upload_image(page_a, img1)
    check(1, "Register, recognize image, prediction appears", test1)

    # TEST 2: History saved; refresh keeps it
    def test2():
        page_a.goto(f"{BASE_URL}/history/")
        expect(page_a.locator(".history-item").first).to_be_visible(timeout=10000)
        page_a.reload()
        expect(page_a.locator(".history-item").first).to_be_visible(timeout=10000)
    check(2, "History saved and persists after refresh", test2)

    # TEST 3: Logout -> protected pages require login
    def test3():
        logout(page_a)
        page_a.goto(f"{BASE_URL}/history/")
        expect(page_a).to_have_url(f"{BASE_URL}/login/", timeout=10000)
    check(3, "Logout and protected pages require login", test3)

    # TEST 4: Login again -> history still there
    def test4():
        login(page_a, USER_A["email"], USER_A["pw"])
        page_a.goto(f"{BASE_URL}/history/")
        expect(page_a.locator(".history-item").first).to_be_visible(timeout=10000)
    check(4, "Login again and history still available", test4)

    # TEST 5: User B registers, cannot see User A's history
    def test5():
        register(page_b, USER_B["name"], USER_B["email"], USER_B["pw"])
        page_b.goto(f"{BASE_URL}/history/")
        expect(page_b.locator(".history-item")).to_have_count(0, timeout=8000)
    check(5, "Second user cannot see first user's history", test5)

print("PART1_DONE")

    # TEST 6: Settings persist across logout/login
    def test6():
        page_a.goto(f"{BASE_URL}/settings/")
        page_a.locator("#setting-autosave").uncheck()
        page_a.get_by_role("button", name="Save").click()
        page_a.wait_for_timeout(1000)
        logout(page_a)
        login(page_a, USER_A["email"], USER_A["pw"])
        page_a.goto(f"{BASE_URL}/settings/")
        expect(page_a.locator("#setting-autosave")).not_to_be_checked(timeout=10000)
    check(6, "Settings persist across logout/login", test6)

    # TEST 7: Delete individual history item
    def test7():
        page_a.goto(f"{BASE_URL}/settings/")
        page_a.locator("#setting-autosave").check()
        page_a.get_by_role("button", name="Save").click()
        page_a.wait_for_timeout(1000)
        upload_image(page_a, img2)
        page_a.goto(f"{BASE_URL}/history/")
        before = page_a.locator(".history-item").count()
        page_a.locator(".history-item .delete-btn").first.click()
        page_a.wait_for_timeout(1500)
        after = page_a.locator(".history-item").count()
        assert after == before - 1, f"count {before} -> {after}"
    check(7, "Delete a history item removes it", test7)

    # TEST 8: Delete account (User B)
    def test8():
        page_b.goto(f"{BASE_URL}/settings/")
        page_b.get_by_role("button", name="Delete Account").click()
        page_b.get_by_role("button", name="Yes, delete my account").click()
        page_b.wait_for_url(f"{BASE_URL}/login/", timeout=10000)
        page_b.goto(f"{BASE_URL}/login/")
        page_b.get_by_placeholder("Email").fill(USER_B["email"])
        page_b.get_by_placeholder("Password", exact=True).fill(USER_B["pw"])
        page_b.get_by_role("button", name="Login").click()
        page_b.wait_for_timeout(1500)
        assert "/login/" in page_b.url or page_b.get_by_text("Invalid").count() > 0, f"account still active? url={page_b.url}"
    check(8, "Delete account and verify it is gone", test8)

    # TEST 9: Every sidebar item opens
    def test9():
        pages = ["/", "/history/", "/explore/", "/modelinfo/", "/settings/"]
        markers = ["Upload an Image", "Recognition History", "Explore", "Model", "Settings"]
        for url, marker in zip(pages, markers):
            page_a.goto(f"{BASE_URL}{url}")
            expect(page_a.get_by_text(marker).first).to_be_visible(timeout=10000)
    check(9, "All sidebar items navigate correctly", test9)

    # Cleanup test images
    import os
    for f in (img1, img2):
        os.path.exists(f) and os.remove(f)

    browser.close()

print("\n===== SUMMARY =====")
fails = [r for r in results if not r[2].startswith("PASS")]
for num, label, status in results:
    print(f"TEST {num}: {label}: {status}")
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
