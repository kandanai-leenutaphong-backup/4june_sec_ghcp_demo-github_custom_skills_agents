# github_custom_skills_agents


Switch to `Hi Agent` and try the following prompt:
1. ```Create a streamline app for Kanban board.```

Change back to main Agent and type the following:

2. ```Write a file main.py to call azure openai model```

You should see the code follows `copilot-instructions.md` to use DefaultAzureCredentials

Try the following skills:

3. ```/meeting-minutes Please generate meeting meeting minutes in assets/transcript.txt for this transcript in the assets/ai-summary.md```

4. ```Write a Python function `get_user_by_email` in a file query.py that takes an email address and returns the matching user row from a `users` table in a PostgreSQL database using psycopg2.```

This will check the `security-and-owasp.instructions.md`


See more of custom skills & Agents at: https://github.com/github/awesome-copilot

Side note on custom PR Review: https://github.com/skills/copilot-code-review/blob/main/.github/steps/3-step.md

## Azure OpenAI retry + logging configuration

The repository includes a retry wrapper in `openai_client.py` and centralized structured logging helpers in `openai_logging.py`.

Set these environment variables to tune retries:

- `AZURE_OPENAI_MAX_RETRIES` (default: `3`)
- `AZURE_OPENAI_RETRY_BASE_SECONDS` (default: `1.0`)
- `AZURE_OPENAI_RETRY_MAX_SECONDS` (default: `8.0`)

Behavior:
- Retries use exponential backoff for HTTP `429` and `5xx` failures.
- Each request attempt writes a structured log entry with `correlation_id`, `attempt`, `status_code`, `success`, and `latency_ms`.