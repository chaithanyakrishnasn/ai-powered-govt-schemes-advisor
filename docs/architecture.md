# Architecture Deep Dive

## Matching Pipeline

**1. Three-Stage Hybrid Retrieval Pipeline**

Our system employs a robust, custom-built matching engine that marries the reliability of deterministic rules with the nuance of semantic search and large language models. The pipeline is divided into three distinct stages to optimize for both speed and accuracy. Stage 1 acts as a highly efficient filter, using a custom SQL rule engine to evaluate hard eligibility constraints like age, income, and state. This step rapidly eliminates up to 75% of irrelevant schemes in approximately 50 milliseconds. 

Stage 2 then takes the remaining candidates and performs a semantic search using `pgvector` and Gemini's `text-embedding-004` (768-dimensional embeddings). By computing the cosine similarity between the user's query and the scheme's embedded text, the engine re-ranks the candidates to ensure the most conceptually relevant schemes bubble to the top. This stage adds only a marginal ~50ms of latency, ensuring the user gets fast initial results.

Stage 3 leverages the reasoning capabilities of Gemini 2.5 Flash to provide personalized explanations. It processes the top 15 candidates by analyzing their raw eligibility text alongside the user's specific profile details. This not only generates a clear, tailored explanation of why the user matches (or doesn't match) but also compensates for complex, unstructured rules that were not captured in Stage 1, acting as a crucial final safety net for accuracy.

**2. LLM-Powered Eligibility Extraction**

One of the biggest challenges in building this system was the source data: government eligibility criteria are typically written in dense, bureaucratic prose that resists simple parsing. To address this, we developed a sophisticated offline extraction pipeline powered by Gemini 2.5 Flash and the `instructor` library. This pipeline ingests raw HTML/JSON descriptions and performs Named Entity Recognition to map the unstructured text into strict Pydantic models. 

These models represent typed operators such as 'equal to' (eq), 'less than or equal to' (lte), 'between', and 'in'. Furthermore, the pipeline captures the logical structure of the rules, grouping them into AND/OR trees, and assigns a confidence score to each extraction. By enforcing strict schemas, we dramatically reduced the incidence of LLM hallucinations, ensuring that the downstream SQL engine operates on highly reliable structured data.

**3. UNKNOWN-Aware Rule Evaluation**

Traditional rule engines often fail brittlely when user data is incomplete—a binary "eligible" or "not eligible" system will incorrectly reject a user if a required field like `caste_category` is missing. We addressed this by designing our evaluation engine with three possible states: PASS, FAIL, and UNKNOWN. 

When the SQL engine encounters a rule requiring a field the user hasn't provided, instead of failing the scheme, it marks that specific rule evaluation as UNKNOWN. The overall scheme match status is then calculated using an optimistic logic: if a scheme has PASS and UNKNOWN results but no FAILs, it is categorized as `LIKELY_ELIGIBLE`. This nuanced approach significantly improves recall, presenting users with potential matches while explicitly highlighting the missing information they need to confirm.

**4. SSE Streaming for Progressive UX**

The sophisticated reasoning performed in Stage 3 by Gemini 2.5 Flash is computationally intensive, taking around 45 seconds to fully process the top 15 schemes. To prevent this latency from degrading the user experience, we implemented a progressive rendering architecture utilizing Server-Sent Events (SSE). 

Instead of waiting for the entire process to complete, the FastAPI backend streams the results in stages. Stage 1 and 2 results are sent almost instantly—scheme cards populate the UI within 500 to 1000 milliseconds. As Stage 3 processes each scheme sequentially, the detailed explanations are streamed down to the client and dynamically injected into the UI. This ensures the application feels highly responsive and interactive, keeping the user engaged while the heavy lifting completes in the background.

**5. Multilingual Retrieval-Augmented Pipeline**

Accessibility is central to this project, meaning it must seamlessly support India's linguistic diversity. We implemented a low-overhead, native-feeling multilingual pipeline that integrates directly with our retrieval architecture. When a user submits a query (e.g., "किसानों के लिए योजनाएं" in Hindi), the backend first performs Unicode script detection to identify the language. 

Because our `pgvector` embeddings are generated in English, the system uses a fast, lightweight LLM call to translate the query into English before performing the semantic search. The core matching pipeline then runs entirely in English. Crucially, during Stage 3, the `SYSTEM_PROMPT` explicitly instructs Gemini to format its final reasoning and explanations back into the user's original language. This approach avoids the cost of maintaining multiple embedding indices while delivering a truly localized experience.

## Data Pipeline

The data pipeline is designed to transform raw, unstructured government data into the highly structured format required by our hybrid retrieval engine. It operates in four distinct phases: Scraping, Extraction, Embedding, and Ingestion.

1.  **Scraping:** We utilize custom web scrapers built with `httpx` for fast asynchronous fetching and `selectolax` for efficient HTML parsing. These scrapers target portals like `myScheme.gov.in` and state-specific sites, extracting raw scheme details and saving them locally as JSONL files. This provides a reproducible snapshot of the raw data.
2.  **Extraction:** This is the core transformation step. A Python script (`extract_one.py` / `ingest.py`) reads the raw JSONL and passes the eligibility text to Gemini via the `instructor` library.
    ```python
    # Example snippet of the extraction logic using Instructor
    class AgeRule(BaseModel):
        operator: Literal["gte", "lte", "between", "eq"]
        min_age: Optional[int]
        max_age: Optional[int]

    class EligibilityRules(BaseModel):
        rules: List[Union[AgeRule, IncomeRule, CasteRule, CustomRule]]
        confidence: float
        
    extracted_data = await client.chat.completions.create(
        model="gemini-2.5-flash",
        response_model=EligibilityRules,
        messages=[{"role": "user", "content": raw_eligibility_text}]
    )
    ```
3.  **Embedding:** Once the rules are structured, the `embed.py` script utilizes Gemini's `text-embedding-004` model to generate 768-dimensional dense vectors representing the scheme's general description and benefits.
4.  **Ingestion:** Finally, the structured data and the generated embeddings are mapped to SQLAlchemy ORM objects and bulk-inserted into the PostgreSQL database, ready for querying by the application.

## Database Schema

The system relies on a PostgreSQL 16 database utilizing 5 core tables, designed to support both rapid SQL filtering and vector similarity search.

1.  **`schemes`:** The central table holding core scheme metadata (title, description, state, ministry). It includes a `search_text` column that concatenates key fields for full-text search fallback.
2.  **`eligibility_rules`:** A crucial table storing the structured rules extracted by the LLM pipeline. It links back to the `schemes` table and includes columns for `rule_type` (e.g., 'age', 'income'), `operator`, and the specific threshold values. This table is heavily indexed to support the Stage 1 SQL filter.
3.  **`scheme_embeddings`:** (Often integrated directly into `schemes` depending on implementation) This table stores the 768-dimensional vector data generated by Gemini. It utilizes the `pgvector` extension, specifically configured for rapid cosine similarity searches during Stage 2 of the pipeline.
4.  **`user_profiles`:** Stores the demographic and socioeconomic data submitted by users via the frontend Wizard. This data is the input for the matching engine.
5.  **`translations`:** (Optional/Cache) Used to cache query translations to minimize LLM overhead for frequently asked questions in regional languages.
