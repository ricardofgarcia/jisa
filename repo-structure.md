# JISA MVP Repository Structure
This structure organizes the Jira Issue Sentiment Analyzer (JISA) MVP into logical directories based on functional components (Prompts, Backend Logic, Frontend UI, and Documentation).

```bash
jisa-issue-sentiment-analyzer/
├── src/
│   ├── backend/
│   │   ├── api_connector.py         # R1: Handles communication with Atlassian MCP & Jira API (data retrieval)
│   │   ├── sentiment_model.py       # R2: Contains the core AI model/logic for sentiment analysis (inference)
│   │   ├── data_processor.py        # Cleans and formats raw Jira text data before sending to the model
│   │   └── main.py                  # Entry point for the core Python service
│   │
│   └── frontend/
│       ├── index.html             # Web App entry point (or App.jsx/App.tsx for React/Angular)
│       ├── styles.css             # Styling for the web app UI
│       └── app.js                 # R4: Handles the UI logic, display of the Markdown, and copying/pasting
│
├── prompts/
│   └── jisa_cursor_prompt.md        # The original prompt template used by the PM in the Cursor interface (AI input instructions)
│
├── report_templates/
│   └── markdown_template.md         # R3: Template defining the required structure for the final Markdown report output
│
├── design_artifacts/
│   ├── jira_sentiment_blueprint.md  # The Service Blueprint (Contextual documentation)
│   └── jira_next_steps_user_stories.md # R1-R4 Jira stories (Requirements documentation)
│
├── config/
│   ├── requirements.txt             # Python dependencies (for the backend/AI code)
│   └── .env.example                 # Environment variables (e.g., API keys, Jira credentials)
│
├── .gitignore
└── README.md                        # Project overview, setup guide, and usage instructions
```