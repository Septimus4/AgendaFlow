"""Answer generation using Mistral LLM."""

from typing import Dict, List, Optional
import logging

from langchain_core.documents import Document
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generate answers using Mistral LLM."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "mistral-small-latest",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        timeout: float = 4.0,
    ):
        """Initialize generator.

        Args:
            api_key: Mistral API key
            model_name: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        logger.info(f"Initializing Mistral LLM: {model_name}")
        self.llm = ChatMistralAI(
            model=model_name,
            mistral_api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    def _format_context(self, documents: List[Document]) -> str:
        """Format documents into context string.

        Args:
            documents: Retrieved documents

        Returns:
            Formatted context string
        """
        context_parts = []

        for i, doc in enumerate(documents, 1):
            metadata = doc.metadata

            # Extract key information
            title = metadata.get("title", "Unknown Event")
            start_datetime = metadata.get("start_datetime", "")
            venue = metadata.get("venue_name", "")
            city = metadata.get("city", "")
            url = metadata.get("url", "")
            price = (
                "Free"
                if metadata.get("is_free")
                else metadata.get("price_bucket", "Price not specified")
            )
            categories = metadata.get("categories", [])
            arrondissement = metadata.get("arrondissement", "")

            # Format date
            try:
                from datetime import datetime
                import pytz

                dt = datetime.fromisoformat(start_datetime)
                paris_tz = pytz.timezone("Europe/Paris")
                dt_paris = dt.astimezone(paris_tz)
                date_str = dt_paris.strftime("%A %d %B %Y, %H:%M")
            except (ValueError, TypeError):
                date_str = start_datetime

            # Build context entry
            context_entry = f"""
Event {i}:
Title: {title}
Date: {date_str}
Venue: {venue}, {city}"""

            if arrondissement:
                context_entry += f" ({arrondissement})"

            context_entry += f"\nPrice: {price}"

            if categories:
                context_entry += f"\nCategories: {', '.join(categories[:3])}"

            if url:
                context_entry += f"\nURL: {url}"

            # Add short description
            content = doc.page_content
            if len(content) > 300:
                content = content[:300] + "..."
            context_entry += f"\nDescription: {content}"

            context_parts.append(context_entry)

        return "\n\n".join(context_parts)

    def _build_system_prompt(self, language: str = "fr") -> str:
        """Build system prompt.

        Args:
            language: Response language

        Returns:
            System prompt
        """
        if language == "en":
            return """You are an event concierge assistant for Paris, France. Your role is to help users find relevant events based on their queries.

Instructions:
- Answer in English, matching the user's language
- Only recommend events from the provided context
- Never invent or hallucinate event information
- If date constraints are specified, ensure all suggestions fall within that range
- If no relevant events are found, clearly state this and suggest the closest alternatives from the context
- Group 3-5 suggestions by theme or date when appropriate
- Always provide: title, date/time, venue, neighborhood/arrondissement (if available), price, and URL
- Avoid listing the same event multiple times; for recurring events, mention the next upcoming date
- Be concise and helpful"""
        else:  # French
            return """Vous êtes un assistant concierge d'événements pour Paris, France. Votre rôle est d'aider les utilisateurs à trouver des événements pertinents selon leurs requêtes.

Instructions :
- Répondez en français, correspondant à la langue de l'utilisateur
- Recommandez uniquement les événements du contexte fourni
- N'inventez jamais d'informations sur les événements
- Si des contraintes de date sont spécifiées, assurez-vous que toutes les suggestions respectent cette plage
- Si aucun événement pertinent n'est trouvé, indiquez-le clairement et suggérez les alternatives les plus proches du contexte
- Groupez 3 à 5 suggestions par thème ou par date si approprié
- Fournissez toujours : titre, date/heure, lieu, quartier/arrondissement (si disponible), prix et URL
- Évitez de lister le même événement plusieurs fois ; pour les événements récurrents, mentionnez la prochaine date
- Soyez concis et utile"""

    def _build_user_prompt(
        self,
        query: str,
        context: str,
        constraints: Optional[Dict] = None,
    ) -> str:
        """Build user prompt.

        Args:
            query: User query
            context: Formatted context
            constraints: Query constraints

        Returns:
            User prompt
        """
        prompt = f"User question: {query}\n\n"

        if constraints:
            prompt += "Constraints:\n"
            if constraints.get("start_date"):
                prompt += f"- Start date: {constraints['start_date']}\n"
            if constraints.get("end_date"):
                prompt += f"- End date: {constraints['end_date']}\n"
            if constraints.get("category"):
                prompt += f"- Category: {constraints['category']}\n"
            if constraints.get("price_constraint"):
                prompt += f"- Price: {constraints['price_constraint']}\n"
            if constraints.get("arrondissement"):
                prompt += f"- Arrondissement: {constraints['arrondissement']}\n"
            prompt += "\n"

        prompt += f"Available events:\n{context}\n\n"
        prompt += (
            "Please provide a helpful response recommending relevant events from the context above."
        )

        return prompt

    def generate(
        self,
        query: str,
        documents: List[Document],
        language: str = "fr",
        constraints: Optional[Dict] = None,
    ) -> Dict:
        """Generate answer from documents.

        Args:
            query: User query
            documents: Retrieved documents
            language: Response language
            constraints: Query constraints

        Returns:
            Dictionary with answer and metadata
        """
        if not documents:
            # No events found
            if language == "en":
                answer = "I couldn't find any events matching your criteria. Please try broadening your search or adjusting the time period."
            else:
                answer = "Je n'ai pas trouvé d'événements correspondant à vos critères. Essayez d'élargir votre recherche ou d'ajuster la période."

            return {
                "answer": answer,
                "events": [],
                "sources": [],
                "filters_applied": constraints or {},
            }

        # Format context
        context = self._format_context(documents)

        # Build prompts
        system_prompt = self._build_system_prompt(language)
        user_prompt = self._build_user_prompt(query, context, constraints)

        # Generate response
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)
            answer = response.content

            # Extract event info for structured output
            events = []
            for doc in documents:
                metadata = doc.metadata
                events.append(
                    {
                        "title": metadata.get("title"),
                        "start_datetime": metadata.get("start_datetime"),
                        "venue_name": metadata.get("venue_name"),
                        "city": metadata.get("city"),
                        "arrondissement": metadata.get("arrondissement"),
                        "price": (
                            "Free" if metadata.get("is_free") else metadata.get("price_bucket")
                        ),
                        "url": metadata.get("url"),
                        "categories": metadata.get("categories", []),
                    }
                )

            sources = [
                metadata.get("url")
                for metadata in [doc.metadata for doc in documents]
                if metadata.get("url")
            ]

            return {
                "answer": answer,
                "events": events,
                "sources": sources,
                "filters_applied": constraints or {},
            }

        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)

            # Fallback response
            if language == "en":
                answer = "I encountered an error generating the response. Here are the events I found:\n\n"
            else:
                answer = "J'ai rencontré une erreur lors de la génération de la réponse. Voici les événements trouvés :\n\n"

            # Add simple list
            for i, doc in enumerate(documents[:3], 1):
                metadata = doc.metadata
                answer += f"{i}. {metadata.get('title')} - {metadata.get('venue_name')}"
                if metadata.get("url"):
                    answer += f"\n   {metadata.get('url')}"
                answer += "\n\n"

            return {
                "answer": answer,
                "events": [],
                "sources": [],
                "filters_applied": constraints or {},
                "error": str(e),
            }
