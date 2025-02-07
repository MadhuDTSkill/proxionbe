from langchain_core.tools import tool
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.document_loaders import UnstructuredURLLoader
import re
from duckduckgo_search.exceptions import RatelimitException
from typing import Annotated

@tool("Wikipedia")
def wikipedia_tool(query: Annotated[str, "The search term to find relevant information from Wikipedia."]) -> str:
    """
    Retrieves a summary from Wikipedia based on the provided query.

    Returns:
        str: A brief summary of the information retrieved from Wikipedia.
    """
    api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=2000)
    wiki = WikipediaQueryRun(api_wrapper=api_wrapper)
    return wiki.run(query)

@tool("DuckDuckGo")
def duckduckgo_search_tool(query: Annotated[str, "The search term to find information from DuckDuckGo."]) -> str:
    """
    Searches the web using DuckDuckGo and returns the results.

    Returns:
        str: The search results obtained from DuckDuckGo or a rate limiting error message.
    """
    try:
        search = DuckDuckGoSearchRun(name="Search")
        return search.run(query)
    except RatelimitException:
        return "Failed to get context from the web due to rate limiting."

@tool("Web URL")
def web_url_tool(url: Annotated[str, "A single URL to retrieve content from."]) -> str:
    """
    Web Scrap the content from the given URL.

    Returns:
        str: A string summarizing the content retrieved from the URL.
    """
    if not url:
        return "No URL provided."

    loader: UnstructuredURLLoader = UnstructuredURLLoader(urls=[url])  
    docs: list = loader.load()  
    content: str = ""  

    for doc in docs:
        content += f"Content: {doc.page_content.strip()}\n\n"  
    return content  

@tool("Developer Biography")
def developer_biography_tool() -> str:
    """
    Returns Developer Biography.

    Returns:
        str: A detailed biography of Madhu.
    """
    biography = """
    Madhu Bagamma Gari is an innovative Python Full Stack Developer with a passion for building advanced applications. Born on 28th March 2000 in Velgode, Nandyal District, Andhra Pradesh, India, Madhu is currently single.

    He completed a Bachelor of Science in Computer Science with a CGPA of 7.5 in December 2021. Madhu's skill set includes Python, Pandas, Data Structures, Numpy, Beautiful Soup, Django, Django ORM, Django Rest Framework, Django Channels (Websockets), MySQL, PostgreSQL, MongoDB, and React.js. He has also developed expertise in generative AI, focusing on utilizing open-source LLM models for creating intelligent applications.

    Currently, Madhu is the lead developer of **Proxima**, a cutting-edge platform similar to ChatGPT that leverages open-source LLM models. The name "Proxima" reflects his fascination with cosmology and is inspired by the Proxima Centauri star system, which captures his interest in the mysteries of the universe.

    Madhu has a deep interest in:
    1. **Cosmology**: Fascinated by the universe, he loves exploring theories about space and time.
    2. **Science Fiction Movies**: Enjoys films that challenge the boundaries of science and imagination, particularly **Prometheus**, which is his favorite Hollywood movie.
    3. **Treasure Hunting**: Captivated by adventure films, especially treasure hunting stories like **Sahasam** from Tollywood.
    4. **AI Ethics**: Advocating for responsible AI use and transparency in AI systems.
    5. **Game Development**: Exploring the intersection of AI and gaming, with plans for a simple game project.
    6. **Community Building**: Actively participates in local tech meetups to foster knowledge sharing and networking among developers.
    7. **Music Production**: Enjoys creating music and experimenting with sound engineering during his free time.
    8. **Traveling**: A passionate traveler, he documents his adventures through vlogs and blogs, sharing insights about different cultures.
    9. **Volunteering**: Engages in various social causes, particularly focusing on education for underprivileged children.
    10. **Fitness Enthusiast**: Regularly practices yoga and jogging to maintain a balanced lifestyle and improve mental health.

    In his free time, Madhu enjoys browsing tech innovations, gaming, and coding, always seeking to learn more about the latest advancements in technology.
    """
    return biography

@tool("Calculator")
def calculator_tool(expression: Annotated[str, "A string containing a mathematical expression"]) -> float:
    """
    Evaluates a basic arithmetic expression and returns the result.
        
    Returns:
        float: The result of the evaluated expression or an error message if invalid.
    """
    # Regular expression to match valid expressions
    valid_pattern = r'^[\d\s+\-*/().]+$'
    
    # Validate the expression
    if not re.match(valid_pattern, expression):
        return "Error: Invalid expression. Only numbers and +, -, *, / operators are allowed."
    
    try:
        # Evaluate the expression
        result = eval(expression)
        return result
    except Exception as e:
        return f"Error: {str(e)}"


tool_status_messages = {
    "Wikipedia" : "Searching on Wikipedia...",
    "DuckDuckGo" : "Searching on DuckDuckGo...",
    "Web URL" : "Scraping the web...",
    "Developer Biography" : "Fetching Developer Biography...",
    "Calculator" : "Calculating..."    
}

# Function to return the status message based on the tool name
def get_tool_status(tool_name):
    return tool_status_messages.get(tool_name, "Unknown tool in use...")


if __name__ == "__main__":
    print(wikipedia_tool("What is the capital of France?"))
    print(duckduckgo_search_tool("What is today's date?"))
    print(web_url_tool("https://python.langchain.com/docs/integrations/"))
    print(developer_biography_tool())
    print(calculator_tool("2 + 2"))