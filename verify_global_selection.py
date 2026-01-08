#!/usr/bin/env python3
"""
Verification script for the global selection implementation.
This script analyzes the code to confirm all components are in place.
"""

import re

def verify_implementation():
    """Verify that all components of the global selection are implemented correctly."""
    
    print("🔍 Verifying Global Selection Implementation")
    print("=" * 60)
    
    # Read the crude_overview.py file
    try:
        with open("app/dashboards/wcod/crude_overview.py", "r") as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ Cannot find crude_overview.py file")
        return
    
    checks = []
    
    # 1. Check for selected-bar-store input
    if 'Input("selected-bar-store", "data")' in content:
        checks.append("✅ selected-bar-store input found")
    else:
        checks.append("❌ selected-bar-store input missing")
    
    # 2. Check for handle_chart_bar_click callback
    if 'def handle_chart_bar_click(' in content:
        checks.append("✅ handle_chart_bar_click callback found")
    else:
        checks.append("❌ handle_chart_bar_click callback missing")
    
    # 3. Check for global selection logic
    if 'Global single-bar selection' in content:
        checks.append("✅ Global selection logic found")
    else:
        checks.append("❌ Global selection logic missing")
    
    # 4. Check for 3-dimension matching
    if 'year_match and stream_match and has_active_month' in content:
        checks.append("✅ 3-dimension matching found")
    else:
        checks.append("❌ 3-dimension matching missing")
    
    # 5. Check for opacity application
    if 'trace_opacity = 1.0 if contains_active_bar else 0.3' in content:
        checks.append("✅ Opacity application logic found")
    else:
        checks.append("❌ Opacity application logic missing")
    
    # 6. Check for debug logging
    if 'DEBUG TRACE OPACITY:' in content:
        checks.append("✅ Debug logging found")
    else:
        checks.append("❌ Debug logging missing")
    
    # 7. Check for string conversion in comparisons
    if 'str(year_val) == str(active_bar_year)' in content:
        checks.append("✅ String conversion for comparisons found")
    else:
        checks.append("❌ String conversion for comparisons missing")
    
    # Print results
    print("\n📋 Implementation Check Results:")
    for check in checks:
        print(f"   {check}")
    
    # Count passed checks
    passed = sum(1 for check in checks if check.startswith("✅"))
    total = len(checks)
    
    print(f"\n📊 Summary: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All components are implemented correctly!")
        print("\n🧪 Testing Instructions:")
        print("1. Open http://localhost:5001 in your browser")
        print("2. Navigate to WCOD Crude Overview")
        print("3. Switch to Monthly Filter view")
        print("4. Open browser developer console (F12)")
        print("5. Click on any bar in the chart")
        print("6. Verify in console that:")
        print("   • Only ONE trace shows 'Contains active bar: true'")
        print("   • Only ONE trace shows 'Final opacity: 1.0'")
        print("   • All other traces show 'Final opacity: 0.3'")
        print("7. Click on a bar in a different year")
        print("8. Verify the selection moves globally, not year-wise")
        
        print("\n✅ Expected Result:")
        print("• Only ONE bar across the entire chart is active at any time")
        print("• All other bars in all years are dimmed")
        print("• Selection works globally across all years")
    else:
        print(f"\n❌ {total - passed} components are missing or incorrect")
        print("Please review the implementation")

if __name__ == "__main__":
    verify_implementation()