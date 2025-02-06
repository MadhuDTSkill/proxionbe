

### **📌 Proxion: Component Breakdown**  

#### **1️⃣ Landing Page (Home)**
- **Features:**
  - Introduction to Proxion: "Explore the Universe with AI."
  - Call-to-action button: **"Get Started"** / **"New Journey"**.
  - Login/Signup options.

#### **2️⃣ Category Selection Page**
- **Sidebar (Right-side menu):**  
  - Categories: **Planets, Stars, Galaxies, Other**.
- **Main screen:**  
  - Displays topics based on the selected category.  
  - Example: If **Planets** → Shows **Neptune, Jupiter, Mars, Saturn, Exoplanets**.
  - Clicking a topic redirects to **Chat Playground**.

#### **3️⃣ Chat Playground (Core Feature)**
- **Interactive Chat UI** (Main Screen)  
  - AI **sends an initial message** based on the selected topic.  
  - Users can chat with Proxion (powered by **LangChain + LLMs**).  
  - **Multimedia Support**: (Future feature) Images, diagrams, interactive visuals.  
- **Sidebar:**  
  - **Chat History:** Users can revisit previous conversations.  
  - **"New Journey" Button:** Allows users to start a new conversation from scratch.

#### **4️⃣ Authentication & User Accounts**
- **Login & Signup with Django Auth + Simple JWT.**
- **User Profiles:**  
  - Saved chat history.  
  - Personalized settings.  
  - Favorite topics? (Optional feature for later).

#### **5️⃣ Fact-based AI Responses**
- **AI will provide sources from NASA, ESA, and research papers.**
- **Potential addition:** Fact-checking module to ensure response credibility.

---
