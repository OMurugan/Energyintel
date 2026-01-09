#!/usr/bin/env python3
"""
Debug script to help identify why global selection isn't working.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_global_selection():
    """Debug the global selection implementation."""
    
    print("🔍 Debugging Global Selection Implementation")
    print("=" * 60)
    
    with open('app/dashboards/wcod/crude_overview.py', 'r') as f:
        content = f.read()
    
    print("📋 Checking Key Components:")
    print()
    
    # Check 1: Selected bar store input
    print("1️⃣ Selected Bar Store Input:")
    if 'Input("selected-bar-store", "data")' in content:
        print("   ✅ selected-bar-store is input to update_breakdown callback")
    else:
        print("   ❌ selected-bar-store missing from update_breakdown inputs")
    
    # Check 2: Selected bar parameter
    print("\n2️⃣ Selected Bar Parameter:")
    if 'def update_breakdown(' in content and 'selected_bar' in content:
        print("   ✅ selected_bar parameter exists in update_breakdown function")
    else:
        print("   ❌ selected_bar parameter missing from update_breakdown function")
    
    # Check 3: Global opacity logic
    print("\n3️⃣ Global Opacity Logic:")
    if 'Apply opacity globally across the entire chart' in content:
        print("   ✅ Global opacity comment found")
    else:
        print("   ❌ Global opacity comment missing")
    
    # Check 4: 3-dimension matching
    print("\n4️⃣ 3-Dimension Matching:")
    if 'year_match' in content and 'month_match' in content and 'stream_match' in content:
        print("   ✅ Enhanced 3-dimension matching found")
    else:
        print("   ❌ Enhanced 3-dimension matching missing")
    
    # Check 5: Debug logging
    print("\n5️⃣ Debug Logging:")
    if 'DEBUG SELECTED_BAR:' in content and 'DEBUG BAR OPACITY:' in content:
        print("   ✅ Comprehensive debug logging found")
    else:
        print("   ❌ Comprehensive debug logging missing")
    
    print("\n🎯 Next Steps for Debugging:")
    print("1. Open browser developer console")
    print("2. Click on any bar in the chart")
    print("3. Look for these debug messages:")
    print("   - 'DEBUG SELECTED_BAR: activeBar found!'")
    print("   - 'DEBUG BAR OPACITY: [stream]-[month]-[year]'")
    print("   - Check if year_match, month_match, stream_match are all true for one bar")
    print("4. If all matches are false, there's a data type or comparison issue")
    print("5. If matches are true but opacity isn't applied, there's a rendering issue")
    
    print("\n🔧 Potential Issues to Check:")
    print("• Data type mismatches (string vs number)")
    print("• Multiple callback executions")
    print("• State not propagating correctly")
    print("• Chart re-rendering overriding opacity")
    
    return True

if __name__ == "__main__":
    debug_global_selection()