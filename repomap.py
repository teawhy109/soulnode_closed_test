# repomap.py
import os, json, re, ast, time
ROOT = "."
PY_MAX_PREVIEW = 120
TEXT_MAX_PREVIEW = 60

def py_symbols(code):
    out = {"functions": [], "classes": [], "flask_routes": []}
    try:
        tree = ast.parse(code)
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef): out["functions"].append(n.name)
            elif isinstance(n, ast.ClassDef): out["classes"].append(n.name)
    except Exception:
        pass
    for m in re.finditer(r"@app\.(get|post|put|delete|route)\(['\"]([^'\"]+)['\"]", code):
        out["flask_routes"].append({"method": m.group(1).upper(), "path": m.group(2)})
    return out

def preview_lines(path, limit):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return "".join(f.readlines()[:limit])
    except Exception:
        return ""

def entry(path):
    stat = os.stat(path)
    item = {
        "path": path.replace("\\","/"),
        "size": stat.st_size,
        "modified": int(stat.st_mtime),
        "ext": os.path.splitext(path)[1].lower(),
    }
    if item["ext"] == ".py":
        code = preview_lines(path, PY_MAX_PREVIEW)
        item["preview"] = code
        item["py"] = py_symbols(code)
    elif item["ext"] in {".md", ".json", ".yaml", ".yml", ".txt"}:
        item["preview"] = preview_lines(path, TEXT_MAX_PREVIEW)
    return item

ignore_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", ".idea", ".vscode"}
result = {"generated_at": int(time.time()), "files": []}

for root, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in ignore_dirs]
    for name in files:
        p = os.path.join(root, name)
        if os.path.getsize(p) > 800_000:
            continue
        result["files"].append(entry(p))

os.makedirs(".sono", exist_ok=True)
with open(".sono/repomap.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
print("Wrote .sono/repomap.json with", len(result["files"]), "entries")