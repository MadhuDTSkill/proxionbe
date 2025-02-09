from pydantic import BaseModel, Field
from typing import List


class ChatNameResponse(BaseModel):
    name: str = Field(..., description="The extracted name representing the chat topic, based on the user's query and LLM response. It should be concise and without suffixes or extra phrases. Max length: 100 characters.")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Black Hole Formation"
            }
        }

class BulletPoints(BaseModel):
    title: str = Field("Untitled", description="A concise title summarizing the key points. It should represent the overall theme of the points.")
    points: List[str] = Field(default_factory=lambda : [], min_items=0, max_items=5, description="A list of key bullet points extracted from the LLM response. Each point should be concise and relevant.")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Black Hole",
                "points": [
                    "A black hole is a region of space where gravity is so strong that nothing, not even light, can escape.",
                    "The event horizon marks the boundary beyond which nothing can return.",
                    "Black holes can form from collapsing massive stars at the end of their life cycle."
                ]
            }
        }