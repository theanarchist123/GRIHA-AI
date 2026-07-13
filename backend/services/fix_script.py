import sys

def fix_file():
    with open('D:/griha_ai/backend/services/broker_call_agent.py', 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if content.startswith('"') and content.endswith('"'):
        content = content[1:-1]
        content = content.replace('\\n', '\n')
        content = content.replace('\\"', '"')
        
    with open('D:/griha_ai/backend/services/broker_call_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_file()
