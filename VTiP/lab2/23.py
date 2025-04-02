import re

def find_csrf_token(html_content):
    csrf_pattern = re.compile(r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"')
    match = csrf_pattern.search(html_content)
    if match:
        return match.group(1)
    return None

# Пример использования
html_content = '''
<form>
    <input type="hidden" name="csrf_token" value="abc123">
</form>
'''
csrf_token = find_csrf_token(html_content)
print(f"CSRF Token: {csrf_token}")
