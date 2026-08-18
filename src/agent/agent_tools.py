import os
import sys
import json
from typing import Dict, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.rag.document_loader import load_local_document
from src.utils.logger import get_logger

logger = get_logger("agent_tools")

def calculate_vacation_accrual(months_worked: float) -> Dict:
    """
    Tool 1: Calculates accrued vacation days based on months worked (1.67 days/month).
    """
    logger.info(f"[Tool Execution] `calculate_vacation_accrual` for {months_worked} months.")
    earned_days = round(float(months_worked) * 1.67, 2)
    return {
        "tool_name": "calculate_vacation_accrual",
        "months_worked": months_worked,
        "accrual_rate_per_month": 1.67,
        "total_earned_days": earned_days
    }

def lookup_employee_profile(employee_id: str) -> Dict:
    """
    Tool 2: Looks up employee department, role, and remaining PTO balance from database.
    """
    logger.info(f"[Tool Execution] `lookup_employee_profile` for ID '{employee_id}'.")
    # Simulated enterprise database lookup
    mock_db = {
        "EMP101": {"name": "Alice Smith", "role": "Senior Engineer", "department": "DevOps", "pto_balance": 14.5},
        "EMP102": {"name": "Bob Jones", "role": "HR Specialist", "department": "Human Resources", "pto_balance": 8.0}
    }
    
    emp_info = mock_db.get(employee_id.upper(), {
        "employee_id": employee_id,
        "name": "Standard Employee",
        "department": "General",
        "pto_balance": 10.0
    })
    
    return {
        "tool_name": "lookup_employee_profile",
        "employee_data": emp_info
    }

def execute_agent_tool(tool_name: str, tool_args: Dict) -> Dict:
    """
    Tool Registry Router: Dispatches tool calls requested by the LLM Agent.
    """
    if tool_name == "calculate_vacation_accrual":
        months = tool_args.get("months_worked", 0)
        return calculate_vacation_accrual(months)
    elif tool_name == "lookup_employee_profile":
        emp_id = tool_args.get("employee_id", "EMP101")
        return lookup_employee_profile(emp_id)
    else:
        return {"error": f"Tool '{tool_name}' is not registered."}

if __name__ == "__main__":
    # Test Tool 1
    t1 = execute_agent_tool("calculate_vacation_accrual", {"months_worked": 8})
    print("--- Tool 1 Test Result ---")
    print(json.dumps(t1, indent=2))
    
    # Test Tool 2
    t2 = execute_agent_tool("lookup_employee_profile", {"employee_id": "EMP101"})
    print("\n--- Tool 2 Test Result ---")
    print(json.dumps(t2, indent=2))
