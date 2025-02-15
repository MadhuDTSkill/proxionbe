# Proxion - AI Chatbot for Cosmology & Astrophysics

Proxion is an advanced AI chatbot designed exclusively for answering questions about cosmology, astrophysics, and space sciences. Built with a combination of **Django (backend), ReactJS (frontend), LangChain & Langraph (LLM integration),** and powerful **LLMs like Groq and Llama**, Proxion provides highly accurate, well-reasoned, and scientifically backed responses about the **universe, galaxies, black holes, dark matter, space-time,** and more.

## Features

### 🌌 Focused on Cosmology
Proxion specializes in **space sciences, astrophysics, and cosmology**, ensuring precise and relevant responses.

### 🤖 Smart Responses
It evaluates, refines, analyzes, and thinks before answering any question, ensuring accuracy and depth in its responses.

### 🎭 Multiple Modes
Choose from different response modes:
- **Scientific Mode** 🧑‍🔬 - Get in-depth, research-backed explanations.
- **Kids Mode** 👦 - Simplified answers for young learners.
- **Casual Mode** ☕ - Friendly, conversational explanations.
- **Story Mode** 📖 - Fun storytelling format to explain complex concepts.

---
## Installation & Setup

### Prerequisites

Ensure you have the following installed:

- Python (>= 3.8)
- Django (>= 4.0)
- Node.js (for frontend integration, optional)
- Redis (for Django Channels)

### Steps to Run

1. **Clone the Repository**

   ```bash
   git clone https://github.com/MadhuDTSkill/proxionbe.git
   cd proxionbe
   ```

2. **Create a Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows use: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Database & Migrations**

   ```bash
   python manage.py migrate
   ```

5. **Run Redis Server (Required for Django Channels if not working)**

   ```bash
   redis-server
   ```

   *(Ensure Redis is installed. If not, install it via ****`brew install redis`**** on macOS or ****`sudo apt install redis`**** on Linux.)*

6. **Run the Django Development Server**

   ```bash
   python manage.py runserver
   ```

7. **Run WebSocket Server**

   ```bash
   daphne -b 0.0.0.0 -p 8001 proxion.asgi:application
   ```

## API Documentation

You can explore API endpoints using Postman:
[API Documentation](https://documenter.getpostman.com/view/23753014/2sA3s9Eokv)

## WebSocket Documentation

Django Channels WebSocket documentation: [Channels Docs](https://channels.readthedocs.io/en/latest/)

## Frontend Repository

The frontend (ReactJS) repository can be found here:
[Proxion Frontend](https://github.com/MadhuDTSkill/proxionfe.git)

---

For any contributions or issues, feel free to raise a PR or an issue on GitHub. 🚀

