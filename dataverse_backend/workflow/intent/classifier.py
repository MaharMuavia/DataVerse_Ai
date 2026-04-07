from workflow.intent.keywords import keyword_classify
from workflow.intent.schema import IntentClassification
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from tenacity import retry, stop_after_attempt, wait_exponential
from workflow.state import AnalysisState
from typing import Dict, Any

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def classify_intent_llm(state: AnalysisState) -> IntentClassification:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    system_prompt = """You are an intent classifier for a Business Intelligence platform called DataVerse AI. The user has uploaded a dataset with these columns: {column_names}. Classify the user's query into one of the following intents: EDA (exploratory data analysis), VIZ (visualization), ML (machine learning prediction), XAI (explainable AI / model explanation), SQL (structured data query), CHITCHAT (general conversation).
Be precise. If the user says 'show me missing values' that is EDA, not VIZ. If they say 'plot a histogram of price' that is VIZ. If they say 'why did the model predict this' that is XAI.
Return ONLY valid JSON matching the schema. No extra text."""

    user_prompt = """Query: {user_query}
Dataset columns: {column_names}
{format_instructions}"""

    parser = PydanticOutputParser(pydantic_object=IntentClassification)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])

    chain = prompt | llm | parser

    result = await chain.ainvoke({
        "user_query": state["user_query"],
        "column_names": state["column_names"],
        "format_instructions": parser.get_format_instructions()
    })

    # Validate target_columns against actual columns
    if result.target_columns:
        result.target_columns = [col for col in result.target_columns if col in state["column_names"]]

    return result

async def classify_intent(state: AnalysisState) -> Dict[str, Any]:
    # Step 1: Try keyword classification
    keyword_result = keyword_classify(state["user_query"])
    if keyword_result:
        return {
            "intent": keyword_result,
            "sub_intent": "",
            "target_columns": [],
            "confidence": 0.85
        }

    # Step 2: LLM classification
    try:
        llm_result = await classify_intent_llm(state)
        return {
            "intent": llm_result.intent,
            "sub_intent": llm_result.sub_intent,
            "target_columns": llm_result.target_columns,
            "chart_type": llm_result.chart_type,
            "model_type": llm_result.model_type,
            "confidence": llm_result.confidence
        }
    except Exception as e:
        # Fallback to CHITCHAT if LLM fails
        return {
            "intent": "CHITCHAT",
            "sub_intent": "",
            "target_columns": [],
            "confidence": 0.5,
            "error_message": f"Intent classification failed: {str(e)}"
        }