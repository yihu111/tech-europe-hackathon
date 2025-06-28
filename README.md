# tech-europe-hackathon

# SkillScope

SkillScope is a hackathon project that reads in a GitHub repository and analyses the profile based on its repos. The information is extracted using a LangGraph-pipeline and then used to search for suitable jobs on the web. For each suggested job, ElevenLabs voice agent can be used for a mock interview based on the job and previous profile analysis and instructive feedback is given. The voice agent has access to a MCP server exposed to the previous analysis based on vector RAG to find tailored questions.

## 🛠️ Features

* **GitHub profile analysis**: Uses a LangGraph pipeline to extract and analyse your repository contents for skills and projects.
* **Web job search**: Employs the analysed profile data to search for and rank relevant job listings on the web.
* **RAG-powered MCP server**: A custom MCP server applies vector-based RAG over your profile analysis and job description to produce tailored interview questions.
* **ElevenLabs mock interviews**: Conduct voice-based mock interviews with an ElevenLabs voice agent using dynamically generated questions. After the interview, the agent generates and delivers personalized feedback and improvement tips based on your responses.

## 🙌 Authors

* Will Foster
* Andy Peng
* Sam Rae
* Lucas Chan
* Yile Huang

Built for **{Tech: Europe} x OpenAI Hackathon – June 2025 – London**
