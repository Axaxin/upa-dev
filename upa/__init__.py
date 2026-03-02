"""UPA package."""

# Re-export symbols from upa.planner_models
from upa.planner_models import Plan, PlanStep, LogicStep

# Note: The main UPA implementation is in upa.py in the project root.
# For testing, import directly from upa.py using importlib:
#   import importlib.util
#   spec = importlib.util.spec_from_file_location("upa_main", "../upa.py")
#   upa_main = importlib.util.module_from_spec(spec)
#   spec.loader.exec_module(upa_main)
#   upa_main.is_trivial_query("你好")
