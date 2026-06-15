"""Script to fix all flow handler indentation issues"""

# For each flow handler, we need to ensure the `if current_step` lines are indented inside the try block

fixes = {
    "app/services/flow_handlers/battery_flow.py": (68, 4),
    "app/services/flow_handlers/workshop_flow.py": (70, 4),
    "app/services/flow_handlers/gps_removed_flow.py": (169, 4),
    "app/services/flow_handlers/gps_damaged_flow.py": (41, 4),
    "app/services/flow_handlers/vehicle_running_flow.py": (42, 4),
    "app/services/flow_handlers/vehicle_standing_flow.py": (48, 4),
    "app/services/flow_handlers/unknown_flow.py": (51, 4),
}

for filepath, (start_line, indent_spaces) in fixes.items():
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # The issue is that after `context = state_manager.get_context(user_phone)`
    # the next lines (# Step X and if current_step) are not indented properly
    # They should be at the same indentation level as the lines inside the try block
    
    fixed_lines = []
    inside_try = False
    try_indent = 0
    
    for i, line in enumerate(lines, 1):
        # Detect try block start
        if line.strip() == "try:":
            inside_try = True
            try_indent = len(line) - len(line.lstrip()) + 4  # Base indent + 4 for try content
            fixed_lines.append(line)
            continue
        
        # Detect except block - this ends the try
        if inside_try and line.strip().startswith("except "):
            inside_try = False
            # Ensure except is at try level (try_indent - 4)
            correct_indent = try_indent - 4
            fixed_lines.append(" " * correct_indent + line.lstrip())
            continue
        
        # If we're past the `context = ...` line and see unindented code
        if inside_try and i >= start_line:
            current_indent = len(line) - len(line.lstrip())
            if current_indent < try_indent and line.strip() and not line.strip().startswith("except"):
                # This line needs to be indented
                fixed_lines.append(" " * try_indent + line.lstrip())
                continue
        
        fixed_lines.append(line)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print(f"Fixed {filepath}")

print("All flows fixed!")
