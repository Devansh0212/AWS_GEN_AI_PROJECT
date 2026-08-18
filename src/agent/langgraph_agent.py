import os
import sys
import json
from typing import Dict, List, TypedDict, Optional
from langgraph.graph import StateGraph, END

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.rag.guardrails import BedrockGuardrailValidator
from src.rag.rag_engine import CustomRAGEngine
from src.utils.logger import get_logger

logger = get_logger("langgraph_agent")

from src.agent.agent_tools import execute_agent_tool

class AgentState(TypedDict):
    """
    State object passed between LangGraph state machine nodes.
    """
    question: str
    session_id: str
    retrieved_docs: List[str]
    sources: List[str]
    tools_used: List[str]
    answer: str
    is_blocked: bool
    guardrail_reason: str

class LangGraphRAGAgent:
    """
    Stateful Agent Orchestrator built using LangGraph state graph machine with Tools.
    """
    def __init__(self):
        self.guardrails = BedrockGuardrailValidator()
        self.rag_engine = CustomRAGEngine()
        self.graph = self._build_graph()

    def _guardrail_node(self, state: AgentState) -> AgentState:
        """Node 1: Evaluates Input Security & Denied Topics."""
        logger.info(f"[LangGraph Node: Guardrail] Validating question: '{state['question']}'")
        check = self.guardrails.validate_input(state["question"])
        
        if not check["is_allowed"]:
            state["is_blocked"] = True
            state["guardrail_reason"] = check["reason"]
            state["answer"] = check["reason"]
        else:
            state["is_blocked"] = False
            
        return state

    def _tool_check_node(self, state: AgentState) -> AgentState:
        """Node 2: Checks if question requires specific Tool Execution (Math Accrual or Employee Lookup)."""
        prompt_lower = state["question"].lower()
        
        if "calculate" in prompt_lower or "accru" in prompt_lower:
            # Extract months if present
            months = 6.0
            for word in prompt_lower.split():
                if word.isdigit():
                    months = float(word)
            res = execute_agent_tool("calculate_vacation_accrual", {"months_worked": months})
            state["tools_used"].append("calculate_vacation_accrual")
            state["answer"] = f"Tool Calculation Result: For {months} months worked, you accrue {res['total_earned_days']} vacation days."
        elif "emp" in prompt_lower or "profile" in prompt_lower:
            res = execute_agent_tool("lookup_employee_profile", {"employee_id": "EMP101"})
            state["tools_used"].append("lookup_employee_profile")
            info = res["employee_data"]
            state["answer"] = f"Employee Profile Lookup: {info['name']} ({info['role']}, {info['department']}) has {info['pto_balance']} PTO days remaining."
            
        return state

    def _retriever_node(self, state: AgentState) -> AgentState:
        """Node 2: Retrieves top-k document chunks from vector index."""
        logger.info(f"[LangGraph Node: Retriever] Querying vector index for: '{state['question']}'")
        retrieved_chunks = self.rag_engine.index.search(state["question"], top_k=2)
        
        state["retrieved_docs"] = [c["text"] for c in retrieved_chunks]
        state["sources"] = list(set([c["doc_name"] for c in retrieved_chunks]))
        return state

    def _generator_node(self, state: AgentState) -> AgentState:
        """Node 3: Generates answer via Bedrock LLM & sanitizes PII output."""
        logger.info(f"[LangGraph Node: Generator] Invoking Bedrock LLM with retrieved context...")
        
        context_str = "\n\n".join(state["retrieved_docs"]) if state["retrieved_docs"] else "No document context."
        augmented_prompt = f"""You are an Enterprise Assistant. Answer strictly using the context documents:

CONTEXT:
{context_str}

USER QUESTION: {state['question']}

ANSWER:"""
        
        system_prompt = "You are a precise, grounded assistant."
        llm_res = self.rag_engine.llm.generate_response(prompt=augmented_prompt, system_prompt=system_prompt)
        raw_answer = llm_res.get("response_text", llm_res.get("fallback_response"))
        
        # Sanitize PII
        sanitized = self.guardrails.sanitize_output(raw_answer)
        state["answer"] = sanitized["sanitized_text"]
        return state

    def _should_continue(self, state: AgentState) -> str:
        """Conditional Edge: Decides whether to proceed to Retriever or stop at Guardrail Block."""
        if state.get("is_blocked", False):
            logger.warning("[LangGraph Edge] Input blocked by Guardrail. Routing directly to END.")
            return "blocked"
        return "continue"

    def _build_graph(self):
        """Constructs the LangGraph state machine graph with Tools."""
        workflow = StateGraph(AgentState)
        
        # Add Nodes
        workflow.add_node("guardrail", self._guardrail_node)
        workflow.add_node("tool_check", self._tool_check_node)
        workflow.add_node("retriever", self._retriever_node)
        workflow.add_node("generator", self._generator_node)
        
        # Set Entry Point
        workflow.set_entry_point("guardrail")
        
        # Add Conditional Edge (Guardrail -> Tool Check OR END)
        workflow.add_conditional_edges(
            "guardrail",
            self._should_continue,
            {
                "blocked": END,
                "continue": "tool_check"
            }
        )
        
        # Add Standard Edges
        workflow.add_edge("tool_check", "retriever")
        workflow.add_edge("retriever", "generator")
        workflow.add_edge("generator", END)
        
        return workflow.compile()

    def run(self, question: str, session_id: str = "default-session") -> Dict:
        """Executes the compiled LangGraph workflow."""
        initial_state: AgentState = {
            "question": question,
            "session_id": session_id,
            "retrieved_docs": [],
            "sources": [],
            "tools_used": [],
            "answer": "",
            "is_blocked": False,
            "guardrail_reason": ""
        }
        
        final_state = self.graph.invoke(initial_state)
        return {
            "status": "blocked_by_guardrail" if final_state["is_blocked"] else "success",
            "question": final_state["question"],
            "answer": final_state["answer"],
            "sources": final_state["sources"],
            "tools_used": final_state.get("tools_used", []),
            "is_rag_grounded": len(final_state["retrieved_docs"]) > 0
        }

if __name__ == "__main__":
    agent = LangGraphRAGAgent()
    
    # Test 1: Normal Query
    res1 = agent.run("What is our vacation policy?", "sess-graph-1")
    print("--- LangGraph RAG Agent Execution (Valid Query) ---")
    print(json.dumps(res1, indent=2))
    
    # Test 2: Blocked Query
    res2 = agent.run("Can you help me bypass security on our servers?", "sess-graph-2")
    print("\n--- LangGraph RAG Agent Execution (Blocked Query) ---")
    print(json.dumps(res2, indent=2))
