#!/usr/bin/env python3
"""Fix tool imports for SessionContext and ToolResult."""
import os

# Directory containing tool files
tools_dir = "app/agents/tools"

# Files to fix
tool_files = [
    "compute_statistics.py",
    "distribution_plot.py",
    "correlation_analysis.py",
    "missing_value_analysis.py",
    "categorical_analysis.py",
    "outlier_detection.py",
    "ask_clarification.py",
    "filter_dataset.py",
    "generate_narrative.py",
    "time_series_trend.py",
    "scatter_relationship.py",
    "group_aggregation.py",
    "compare_segments.py",
    "custom_metric_calculator.py",
    "train_classifier.py",
    "train_regressor.py",
    "explain_model_global.py",
    "explain_prediction_local.py",
    "counterfactual_explainer.py"
]

fixed_count = 0
for filename in tool_files:
    filepath = os.path.join(tools_dir, filename)
    if not os.path.exists(filepath):
        print(f"⊘ {filename} not found")
        continue
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if SessionContext/ToolResult are already imported
    if 'from ..core.tool_registry import' in content:
        print(f"✓ {filename} already has correct import")
        continue
    
    # Add the import after "from .base_tool import BaseTool"
    if 'from .base_tool import BaseTool' in content:
        old = "from .base_tool import BaseTool\n"
        new = "from .base_tool import BaseTool\nfrom ..core.tool_registry import SessionContext, ToolResult\n"
        new_content = content.replace(old, new, 1)
        
        if new_content != content:
            with open(filepath, 'w') as f:
                f.write(new_content) 
            print(f"✓ Fixed {filename}")
            fixed_count += 1
        else:
            print(f"! Could not replace in {filename}")
    else:
        print(f"! {filename} - no base import found")

print(f"\nFixed {fixed_count} files")
