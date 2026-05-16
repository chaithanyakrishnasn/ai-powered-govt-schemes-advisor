from google import genai
from google.genai import types
from app.services.llm.gemini import GeminiClient
from app.services.matching.service import MatchingService
from app.schemas.user_profile import UserProfile
from app.schemas.match import SchemeResultItem
import json

CHAT_SYSTEM_PROMPT = """You are Yojana AI, a helpful assistant that helps Indian citizens discover and understand government schemes and benefits.

You have access to a database of 334+ Indian government schemes covering agriculture, education, health, housing, disability, women empowerment, and more.

Your capabilities:
1. Answer questions about specific government schemes (eligibility, benefits, application process)
2. Search for schemes matching the user's needs when they ask for recommendations
3. Explain complex government policies in simple language
4. Help users understand if they qualify for specific schemes
5. Guide users through application processes

When to search for schemes:
- User asks "show me schemes", "what schemes am I eligible for", "find schemes for..."
- User asks about a category ("farming schemes", "education scholarships", "disability benefits")
- User asks "what can I get" or "what benefits am I entitled to"

When NOT to search for schemes (just answer conversationally):
- User asks "what is [scheme name]?" → explain it
- User asks "how do I apply for [scheme]?" → explain the process
- User asks general questions about government policies
- User greets or asks meta questions
- User asks follow-up questions about a scheme already discussed

User profile context (use this to personalize responses):
{profile_context}

Important rules:
- Never invent scheme details. If you don't know, say so.
- Always respond in {language_name}.
- Keep responses concise and practical.
- When you search for schemes, briefly explain WHY these schemes match before listing them.
- Use simple language — many users are from rural areas with limited formal education.
"""

SCHEME_SEARCH_TRIGGERS = [
    "show me", "find me", "what schemes", "which schemes",
    "schemes for", "eligible for", "benefits for", "yojana for", "yojana",
    "योजना", "योजनाएं", "ಯೋಜನೆ", "ಯೋಜನೆಗಳು",
    "subsidy", "scholarship", "pension", "assistance", "support",
    "what can i get", "what am i eligible", "recommend",
]

def should_search_schemes(message: str) -> bool:
    message_lower = message.lower()
    return any(trigger in message_lower for trigger in SCHEME_SEARCH_TRIGGERS)

class ChatService:
    def __init__(
        self,
        gemini_client: GeminiClient,
        matching_service: MatchingService,
    ):
        self.gemini_client = gemini_client
        self.matching_service = matching_service

    async def chat(
        self,
        message: str,
        history: list[dict],
        profile: UserProfile | None,
        language: str = "en",
    ) -> dict:
        profile_context = self._build_profile_context(profile)
        
        system = CHAT_SYSTEM_PROMPT.format(
            profile_context=profile_context or "No profile provided",
            language_name={"en": "English", "hi": "Hindi", "kn": "Kannada"}.get(language, "English")
        )
        
        search_triggered = should_search_schemes(message)
        schemes_to_return = None
        scheme_context = ""
        
        if search_triggered and self.matching_service:
            results, candidates, _ = await self.matching_service.match_profile(
                profile=profile or UserProfile(),
                query=message,
                max_results=5,
                explain=False,
                language=language,
            )
            top_results = results[:5]
            
            candidate_map = {c.id: c for c in candidates}
            
            # Build context string for the LLM
            scheme_context = "\nRelevant schemes found in database:\n"
            for r in top_results:
                full_scheme = candidate_map.get(r.scheme_id)
                if full_scheme:
                    description = full_scheme.benefit_description or 'No description'
                    scheme_context += f"- {r.name} ({r.status}): {description}\n"

            # Build rich SchemeResultItem objects for the frontend
            result_items = []
            for r in top_results:
                full_scheme = candidate_map.get(r.scheme_id)
                if full_scheme:
                    item = SchemeResultItem(
                        scheme_id=r.scheme_id,
                        slug=r.slug,
                        name=r.name,
                        status=r.status,
                        score=r.score,
                        level=full_scheme.level,
                        state=full_scheme.state,
                        categories=full_scheme.categories,
                        benefit_type=full_scheme.benefit_type,
                        benefit_description=full_scheme.benefit_description,
                        application_url=full_scheme.application_url,
                        missing_fields=r.missing_fields,
                    )
                    result_items.append(item)
            schemes_to_return = result_items
        
        contents = []
        for msg in history[-10:]:
            contents.append(types.Content(
                role=msg["role"],
                parts=[types.Part(text=msg["content"])]
            ))
        
        user_content = message
        if scheme_context:
            user_content = f"""{message}

[Context from scheme database: {scheme_context}]"""
        
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=user_content)]
        ))
        
        try:
            response = await self.gemini_client.raw_client.aio.models.generate_content(
                model_name="models/gemini-2.5-flash",                contents=contents,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1000,
                ),
                system_instruction=system
            )
            text_response = response.text or "I could not generate a response."
        except Exception as e:
            text_response = "Sorry, I encountered an error while trying to generate a response. The API key might be invalid or there could be a network issue."
            print(f"Chat generation failed: {e}")

        return {
            "response": text_response,
            "schemes": [s.model_dump() for s in schemes_to_return] if schemes_to_return else None,
            "should_show_schemes": search_triggered and schemes_to_return is not None,
        }

    def _build_profile_context(self, profile: UserProfile | None) -> str:
        if not profile:
            return ""
        parts = []
        if profile.age: parts.append(f"Age: {profile.age}")
        if profile.state: parts.append(f"State: {profile.state}")
        if profile.is_farmer: parts.append("Occupation: Farmer")
        if profile.annual_income: parts.append(f"Income: ₹{profile.annual_income:,.0f}/year")
        if profile.caste_category: parts.append(f"Category: {profile.caste_category}")
        if profile.has_disability: parts.append("Has disability")
        if profile.education_level: parts.append(f"Education: {profile.education_level}")
        return ", ".join(parts)
