from typing import TypedDict, List, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END



# -------------------------------
# Define Data Schemas & State
# -------------------------------

PROXION = """
    You are Proxion, an advanced AI created by Madhu Sunil, specializing in cosmology, astrophysics, and space sciences. You strictly answer only space-related questions.

    ### Guidelines:
    1. Scope: Only respond to cosmology and space science topics. Politely decline unrelated queries.
    2. Accuracy: Base answers on scientific research (NASA, ESA, arXiv, peer-reviewed papers). Acknowledge ongoing research when necessary.
    3. Unanswered Questions: If uncertain, provide hypotheses and mention ongoing studies.
    4. Complexity: Adjust explanations for beginners and experts accordingly.
    5. No Speculation: Avoid pseudoscience and misinformation; clarify scientific consensus.
    6. Encourage Learning: Suggest research papers or resources for deeper exploration.
    7. Engaging Tone: Be conversational, clear, and natural—like an expert, not a machine.
    8. Concise Answers: Keep responses brief and to the point. Expand only if requested.
"""


class State(TypedDict):
    user_query: str
    sections: List[str]
    selected_mode: Literal["Casual", "Scientific", "Story"]
    generated_response: str
    refined_response: str
    is_satisfactory: bool
    feedback: str

class SectionsOutput(BaseModel):
    sections: List[str] = Field(description="Relevant sections for this topic.")
    
    
class InitialOutput(BaseModel):
    response: str = Field(description="Generated response to user provided query.")

class ResponseFeedback(BaseModel):
    is_satisfactory: bool = Field(description="Indicates if the response is scientifically accurate and complete.")
    feedback: str = Field(description="Feedback on how to improve the answer if needed.")

class ProxionWorkflow:
    def __init__(self, llm, verbose=False):
        self.llm = llm
        self.verbose = verbose
        self.section_generator = self.llm.with_structured_output(SectionsOutput)
        self.initial_output = self.llm.with_structured_output(InitialOutput)
        self.evaluator = self.llm.with_structured_output(ResponseFeedback)
        self.workflow = self._build_workflow()

    def _verbose_print(self, message: str):
        if self.verbose:
            print(f"\033[92m[VERBOSE] {message}\033[0m")

    def _build_workflow(self):
        builder = StateGraph(State)
        builder.add_node("generate_sections", self.generate_sections)
        builder.add_node("multi_step_thinking", self.multi_step_thinking)
        builder.add_node("apply_explanation_mode", self.apply_explanation_mode)
        builder.add_node("evaluate_response", self.evaluate_response)
        builder.add_node("refine_response", self.refine_response)

        builder.add_edge(START, "generate_sections")
        builder.add_edge("generate_sections", "multi_step_thinking")
        builder.add_edge("multi_step_thinking", "apply_explanation_mode")
        builder.add_edge("apply_explanation_mode", "evaluate_response")
        builder.add_edge("refine_response", "evaluate_response")

        builder.add_conditional_edges(
            "evaluate_response",
            lambda state: "Not Satisfied" if not state["is_satisfactory"] else "Satisfied",
            {"Not Satisfied": "refine_response", "Satisfied": END}
        )
        return builder.compile()

    def generate_sections(self, state: State) -> dict:
        self._verbose_print("Generating sections for the given query.")
        result = self.section_generator.invoke(
            f"Break down the topic '{state['user_query']}' into key sections."
        )
        self._verbose_print(f"Generated Sections: {result.sections}")
        return {"sections": result.sections}

    def multi_step_thinking(self, state: State) -> dict:
        self._verbose_print("Generating response using structured sections.")
        sections_text = " ".join([f"Section: {s}" for s in state["sections"]])
        response = self.initial_output.invoke(f"Using the following sections, generate a well-structured response: {sections_text}")
        self._verbose_print(f"Generated Response: {response.response}")
        return {"generated_response": response.response}

    def apply_explanation_mode(self, state: State) -> dict:
        base_response = state["generated_response"]
        mode = state.get("selected_mode", "Casual")
        if mode == "Scientific":
            modified_response = f"[Technical Explanation] {base_response}"
        elif mode == "Story":
            modified_response = f"Imagine this scenario: {base_response}"
        else:
            modified_response = base_response
        self._verbose_print(f"Applied Mode ({mode}): {modified_response}")
        return {"refined_response": modified_response}

    def evaluate_response(self, state: State) -> dict:
        self._verbose_print("Evaluating response for accuracy.")
        evaluation = self.evaluator.invoke(f"Evaluate: {state['refined_response']}")
        self._verbose_print(f"Evaluation Result: {evaluation.is_satisfactory}, Feedback: {evaluation.feedback}")
        return {"is_satisfactory": evaluation.is_satisfactory, "feedback": evaluation.feedback}

    def refine_response(self, state: State) -> dict:
        if not state["is_satisfactory"]:
            self._verbose_print("Refining response based on feedback.")
            improved = self.llm.invoke(f"Refine: {state['refined_response']} based on feedback: {state['feedback']}")
            self._verbose_print(f"Refined Response: {improved.content}")
            return {"refined_response": improved.content}
        return {}

    def run(self, user_query: str, selected_mode: str = "Casual") -> str:
        initial_state = {"user_query": user_query, "selected_mode": selected_mode}
        final_state = self.workflow.invoke(initial_state)
        return final_state["refined_response"]

# -------------------------------
# Example Usage
# -------------------------------

from langchain_groq import ChatGroq

llm_instance = ChatGroq(model="llama-3.3-70b-versatile")
proxion = ProxionWorkflow(llm_instance, verbose=True)
answer = proxion.run("Explain about our 8 planets.", selected_mode="Scientific")
print("\nFinal Answer:", answer)