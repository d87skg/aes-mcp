path = 'stateful_risk_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old2 = '''f"Auto-meltdown: {cr["description"]}"'''
new2 = '''f"Auto-meltdown: {desc}"'''
content = content.replace(old2, new2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("V2.1 second f-string fix applied")