path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''                reason = f"Composite pattern detected: {cr["description"]}"'''
new = """                desc = cr["description"]
                reason = f"Composite pattern detected: {desc}\""""
content = content.replace(old, new)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("V2.1 f-string fix applied")