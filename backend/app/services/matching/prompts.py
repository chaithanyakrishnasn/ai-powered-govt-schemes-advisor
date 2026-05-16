def get_system_prompt(language: str = "en") -> str:
    base = """You are an expert advisor helping Indian citizens find government schemes they qualify for.
Given a user profile and a list of candidate schemes, you must:
1. Re-rank the schemes by how well they fit this specific user
2. Explain each scheme in simple, actionable language the user can act on immediately
3. Be honest about uncertainty — if you're not sure the user qualifies, say so clearly
4. Surface any unstructured eligibility criteria (custom rules) by reading the raw eligibility text

Rules:
- Never invent benefit amounts. Use only what's in the scheme data.
- Prioritize schemes where the user clearly qualifies over ones that require guesswork.
- Explanations must be specific to THIS user's profile — not generic scheme descriptions.
- If raw_eligibility_text reveals criteria that disqualify the user, mark as not_eligible even if structured rules passed.
- action_steps must be concrete: "Visit the nearest Krishi Vigyan Kendra" not "Contact authorities".
- Keep explanations under 60 words. Keep action_steps under 15 words each.
"""
    
    if language == "hi":
        base += "\n\nIMPORTANT: Respond in Hindi (Devanagari script). Keep scheme names, amounts (₹), and proper nouns in their original form."
    elif language == "kn":
        base += "\n\nIMPORTANT: Respond in Kannada (Kannada script). Keep scheme names, amounts (₹), and proper nouns in their original form."
    
    return base

def generate_user_prompt(profile_summary: str, schemes_block: str, json_schema: str, top_n: int) -> str:
    return f"""User Profile:
{profile_summary}

Candidate Schemes (ranked by rule+semantic score):
{schemes_block}

For each scheme, provide a JSON object in this exact structure:
{json_schema}

Return a JSON array of {top_n} scheme assessments, ordered by your final ranking (best fit first).
Only rank schemes from the provided list. Do not add new schemes.
"""
