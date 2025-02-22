from typing import TypedDict, List, Literal, Dict
from pydantic import BaseModel, Field


class WorkFlowState(TypedDict):
    _verbose : bool
    _consumer: object
    is_cosmology_related: bool
    user_query: str
    thoughts: str
    selected_mode: Literal["Casual", "Scientific", "Story", "Kids"]
    generated_response: str
    tool_responses : Dict[str, str]
    refined_response: str
    final_response: Dict[str, str]

    
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
                    "If the query is related to cosmology:\n"
                    "- retun empty string like ''"
    )
    
  
  
class ThinkingOutput(BaseModel):
    thoughts: str = Field(
        description="Internal thoughts & discussion about the user query."
    )
    requires_tool_call: bool = Field(
        description="Indicates whether external knowledge, real-time data, or the latest sources (e.g., Wikipedia, Arxiv, DuckDuckGo) "
                    "are required to enhance the response based on the user query."
    )
    

class ProxionPerspectiveOutput(BaseModel):
    response: str = Field(
        description=(
            "The **Proxion View** is a unique perspective derived from available theories, offering a speculative yet logical "
            "insight on the given topic. It presents an imaginative yet thoughtful take, aiming to spark curiosity and new ways "
            "of thinking. While grounded in scientific concepts, it explores possibilities beyond conventional understanding, "
            "bridging known facts with intriguing speculation. The response is always a **single paragraph**, strictly between "
            "1 to 10 sentences, ensuring a concise yet impactful perspective."
        )
    )
