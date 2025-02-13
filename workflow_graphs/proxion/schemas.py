from typing import TypedDict, List, Literal, Dict
from pydantic import BaseModel, Field


class WorkFlowState(TypedDict):
    _verbose : bool
    _consumer: object
    is_cosmology_related: bool
    user_query: str
    sections: List[str]
    expansion_sections : List[str]
    selected_mode: Literal["Casual", "Scientific", "Story", "Kids"]
    generated_response: str
    tool_responses : Dict[str, str]
    refined_response: str
    final_response: Dict[str, str]
    is_satisfactory: bool
    requires_tool_call : bool
    feedback: str


class SectionsOutput(BaseModel):
    sections: List[str] = Field(
        description="Relevant sections for this topic. The response will always contain general sections based on the user query. "
                    "If the question involves speculative ideas or hypotheses, additional perspectives will be appended: "
                    "Scientific View (scientific explanation based on physics and cosmology), "
                    "Theoretical View (hypotheses and speculative models), "
                    "Philosophical View (exploring meaning and existential implications), "
                    "Proxion View (AI-generated perspective creatively inferred from knowledge)."
    )
    
    
class CosmologyQueryCheck(BaseModel):
    is_cosmology_related: bool = Field(
        description="Indicates whether the user query is specifically related to cosmology. "
                    "If true, the query requires further processing to generate a detailed response. "
                    "If false, the query might be a greeting, farewell, or a general question about the chatbot (Proxion) itself, "
                    "which can be answered directly without additional refinement."
    )
    response: str = Field(
        description="If the query is not related to cosmology:\n"
                    "- For greetings (e.g., 'Hi', 'Hello'), respond warmly (e.g., 'Hi! How can I assist you today?').\n"
                    "- For farewells (e.g., 'Goodbye', 'See you'), respond appropriately (e.g., 'Goodbye! Have a great day!').\n"
                    "- For chatbot-related queries (e.g., 'Who are you?'), provide relevant details (e.g., 'I am Proxion, an AI assistant created by Madhu Bagamma Gari, specializing in cosmology and space sciences.').\n"
                    "- For completely unrelated questions (e.g., 'Who is Modi?'), politely inform the user that Proxion only focuses on cosmology (e.g., 'I focus only on cosmology-related topics. Let’s talk about the wonders of the universe!')."
    )
    requires_tool_call: bool = Field(
        description="Indicates whether external knowledge, real-time data, or the latest sources (e.g., Wikipedia, Arxiv, DuckDuckGo) "
                    "are required to enhance the response based on the user query."
    )
  

class ResponseFeedback(BaseModel):
    is_satisfactory: bool = Field(description="Indicates if the response is scientifically accurate and complete.")
    feedback: str = Field(description="Feedback on how to improve the answer if needed.")

