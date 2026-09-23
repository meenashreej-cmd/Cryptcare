import sys
import os
from fastapi import routing

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

def generate_inventory():
    with open("route_inventory.md", "w", encoding="utf-8") as f:
        f.write("| Method | Path | Endpoint Name | Explicit Role/Dependency |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                methods = ", ".join(route.methods - {"OPTIONS"}) if route.methods else "GET"
                path = route.path
                name = route.name
                
                dependencies = []
                if hasattr(route, "dependant") and hasattr(route.dependant, "dependencies"):
                    for d in route.dependant.dependencies:
                        dep_name = d.call.__name__ if hasattr(d.call, "__name__") else str(d.call)
                        
                        if "require_role" in dep_name or "_dependency" in dep_name or "RoleChecker" in dep_name:
                            # extract role from closure if possible
                            closure = getattr(d.call, "__closure__", None)
                            roles = []
                            if closure:
                                for cell in closure:
                                    if isinstance(cell.cell_contents, tuple) or isinstance(cell.cell_contents, list):
                                        roles.extend(cell.cell_contents)
                                    elif isinstance(cell.cell_contents, str):
                                        roles.append(cell.cell_contents)
                            if roles:
                                dependencies.append(f"require_role({','.join(roles)})")
                            else:
                                dependencies.append(f"require_role")
                        elif "get_current_user" in dep_name:
                            dependencies.append("get_current_user")
                        else:
                            dependencies.append(dep_name)
                        
                dep_str = ", ".join(dependencies) if dependencies else "⚠️ None"
                f.write(f"| **{methods}** | `{path}` | `{name}` | {dep_str} |\n")

if __name__ == "__main__":
    generate_inventory()
