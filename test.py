from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import List

model = ChatGroq(
    model = "llama-3.3-70b-versatile",
    temperature=0.1,
)

class BulletPoints(BaseModel):
    title: str = Field(..., description="A concise title summarizing the key points. It should represent the overall theme of the points.")
    points: List[str] = Field(..., min_items=0, max_items=5, description="A list of key bullet points extracted from the LLM response. Each point should be concise and relevant.")
    
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

structured_llm = model.with_structured_output(BulletPoints)

res= structured_llm.invoke("""The Sun! Our star, the center of our solar system. Here are some fascinating facts about the Sun:

    The Sun is a massive ball of hot, glowing gas, primarily composed of hydrogen and helium. It has a diameter of approximately 1.4 million kilometers (870,000 miles), which is about 109 times larger than the diameter of the Earth.

    The Sun's surface temperature is about 5,500°C (10,000°F), but its core is a scorching 15,000,000°C (27,000,000°F). This intense heat energy is produced by nuclear reactions that occur within the core, where hydrogen atoms are fused into helium, releasing vast amounts of energy in the process.

    The Sun is so massive that it makes up about 99.8% of the mass of our solar system, with the remaining 0.2% consisting of the planets, dwarf planets, asteroids, comets, and other objects that orbit around it.

    The Sun's gravity holds our solar system together, keeping the planets in their orbits. Without the Sun's gravity, the planets would fly off into space.

    The Sun is about 4.6 billion years old and has already burned through about half of its hydrogen fuel. It will continue to shine for another 5 billion years or so before running out of fuel and becoming a red giant, engulfing the inner planets, including Earth.

    The Sun's energy is essential for life on Earth, powering the Earth's climate and weather patterns, as well as providing the energy that plants need to undergo photosynthesis.

    The Sun is also responsible for the beautiful phenomenon of sunrises and sunsets, which occur when the Sun's rays pass through the Earth's atmosphere, scattering shorter wavelengths of light, such as blue and violet, and leaving mainly longer wavelengths, like red and orange, to reach our eyes.

    These are just a few of the many fascinating facts about the Sun. Is there anything specific you'd like to know more about?""")

print(res.model_dump())

