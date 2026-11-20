
class PlannerAgent:
    def __init__(self, model_client):
        self.model = model_client

    def run(self, requirement):
        system_prompt = """
You are a senior software architect and Planner Agent.

Your job:
1. Understand the software requirement.
2. Break it into development tasks.
3. Define the target files.
4. Define acceptance criteria.
5. Identify edge cases and risks.

Return a structured Markdown development plan.

Do not claim that code or tests already exist.
Do not invent test results.
"""

        return self.model.generate(
            system_prompt=system_prompt,
            user_prompt=requirement,
        )
