import os
import ast
import importlib.util
from collections import defaultdict

def get_all_py_files(base_path):
    py_files = []
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
    return py_files

def get_imported_modules_from_file(file_path):
    imported = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            node = ast.parse(f.read(), filename=file_path)
        for n in ast.walk(node):
            if isinstance(n, ast.Import):
                for alias in n.names:
                    imported.add(alias.name.split('.')[0])
            elif isinstance(n, ast.ImportFrom):
                if n.module:
                    imported.add(n.module.split('.')[0])
    except Exception as e:
        print(f"⚠️ 無法解析 {file_path}: {e}")
    return imported

def is_module_installed(module_name):
    return importlib.util.find_spec(module_name) is not None

def main():
    base_dir = "."
    all_py_files = get_all_py_files(base_dir)
    module_usage_map = defaultdict(list)
    all_imports = set()

    for file in all_py_files:
        imports = get_imported_modules_from_file(file)
        for mod in imports:
            module_usage_map[mod].append(file)
            all_imports.add(mod)

    print("🔍 檢查未安裝的模組及其使用位置：\n")

    has_missing = False
    for mod in sorted(all_imports):
        if not is_module_installed(mod):
            has_missing = True
            print(f"❌ 未安裝模組：{mod}")
            for file in sorted(module_usage_map[mod]):
                print(f"   └── 被使用於：{file}")
            print()

    if not has_missing:
        print("✅ 所有模組都已安裝。")

if __name__ == "__main__":
    main()

