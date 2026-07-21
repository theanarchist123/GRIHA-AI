import os, re

base_dir = r"d:\griha_ai\frontend\src"
updated = 0

for root, _, files in os.walk(base_dir):
    for f in files:
        if f.endswith(".tsx") or f.endswith(".ts"):
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()
            
            # Replace backtick URLs
            new_content = re.sub(r"`http://localhost:10000(/.*?)`", r"`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}\1`", content)
            
            # Replace double quote URLs
            new_content = re.sub(r'"http://localhost:10000(/.*?)"', r"`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}\1`", new_content)
            
            # Replace single quote URLs
            new_content = re.sub(r"'http://localhost:10000(/.*?)'", r"`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}\1`", new_content)
            
            if content != new_content:
                with open(path, "w", encoding="utf-8") as file:
                    file.write(new_content)
                print(f"Updated {path}")
                updated += 1

print(f"Done. Updated {updated} files.")
