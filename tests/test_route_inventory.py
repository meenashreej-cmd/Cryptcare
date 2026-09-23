import os
import subprocess
import pytest

def test_route_inventory_script_runs():
    """Test that the route inventory generation script runs successfully."""
    script_path = os.path.join("scripts", "generate_route_inventory.py")
    assert os.path.exists(script_path), f"Script not found at {script_path}"
    
    # Run the script
    result = subprocess.run(["python", script_path], capture_output=True, text=True)
    assert result.returncode == 0, f"Script failed with output: {result.stderr}"
    
    # Check that it generated the file
    inventory_path = "route_inventory.md"
    assert os.path.exists(inventory_path), f"Inventory file not found at {inventory_path}"
    
    with open(inventory_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "| Method | Path | Endpoint Name | Explicit Role/Dependency |" in content
