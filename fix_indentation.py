"""
Quick script to fix indentation in flow handler files
"""
import os

flow_handlers = [
    "app/services/flow_handlers/battery_flow.py",
    "app/services/flow_handlers/workshop_flow.py",
    "app/services/flow_handlers/gps_removed_flow.py",
    "app/services/flow_handlers/gps_damaged_flow.py",
    "app/services/flow_handlers/vehicle_running_flow.py",
    "app/services/flow_handlers/vehicle_standing_flow.py",
    "app/services/flow_handlers/unknown_flow.py",
]

for handler_path in flow_handlers:
    if not os.path.exists(handler_path):
        print(f"Skipping {handler_path} - file not found")
        continue
    
    with open(handler_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the problematic pattern: context = ... followed by unindented if
    fixed_lines = []
    in_try_block = False
    
    for i, line in enumerate(lines):
        # Detect if we just entered try block
        if "def handle_" in line and "_flow(" in line:
            in_try_block = False
        
        if line.strip().startswith("try:"):
            in_try_block = True
            fixed_lines.append(line)
            continue
        
        # If we're in try block and see an unindented if/elif after context line
        if in_try_block and i > 0:
            prev_line = lines[i-1]
            if "context = state_manager.get_context" in prev_line:
                # Next line should be the step check - needs to be indented
                if line.strip().startswith("# Step") or line.strip().startswith("if current_step"):
                    # Make sure it's indented at try block level + 4
                    fixed_lines.append("    " + line.lstrip())
                    continue
        
        fixed_lines.append(line)
    
    # Write back
    with open(handler_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print(f"Fixed {handler_path}")

print("Done fixing indentation!")
