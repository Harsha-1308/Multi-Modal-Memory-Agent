import base64
import io
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
from app.core.config import settings
from app.integrations.groq_client import GroqClient

logger = logging.getLogger(__name__)


ALLOWED_IMAGE_MIMES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
}

ALLOWED_TEXT_MIMES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "text/html",
    "text/x-python",
    "application/json",
    "application/javascript",
    "application/x-yaml",
    "text/yaml",
}

ALLOWED_DOC_MIMES = {
    "application/pdf",
}

ALL_ALLOWED_MIMES = ALLOWED_IMAGE_MIMES | ALLOWED_TEXT_MIMES | ALLOWED_DOC_MIMES


class EvidenceUnderstandingService(ABC):
    @abstractmethod
    def analyze_image(
        self,
        *,
        file_bytes: bytes,
        mime_type: str,
        user_description: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Returns (semantic_description, combined_understanding).
        """
        pass

    @abstractmethod
    def analyze_document(
        self,
        *,
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
        user_description: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Returns (semantic_description, combined_understanding).
        """
        pass

    @abstractmethod
    def process_evidence(
        self,
        *,
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
        user_description: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """
        Determines kind and returns (kind, semantic_description, combined_understanding).
        """
        pass


class GroqEvidenceUnderstandingService(EvidenceUnderstandingService):
    def __init__(
        self,
        groq_client: Optional[Any] = None,
        vision_model: Optional[str] = None,
        text_model: Optional[str] = None,
    ):
        self.groq_wrapper = groq_client or GroqClient()
        self.vision_model = vision_model or settings.GROQ_VISION_MODEL
        self.text_model = text_model or settings.GROQ_MODEL

    def _get_client(self):
        return getattr(self.groq_wrapper, "client", self.groq_wrapper)

    def analyze_image(
        self,
        *,
        file_bytes: bytes,
        mime_type: str,
        user_description: Optional[str] = None,
    ) -> Tuple[str, str]:
        client = self._get_client()
        b64_image = base64.b64encode(file_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64_image}"

        user_statement = (user_description or "").strip()
        system_prompt = (
            "You are an expert technical visual analysis assistant. "
            "Analyze the uploaded image thoroughly. If it contains a code error, stack trace, "
            "UI issue, terminal output, diagram, or system state, describe exactly what is shown, "
            "including specific error messages, components, line numbers, or visual anomalies. "
            "Be factual, concise, and structured. Do not invent details."
        )

        prompt_text = "Please analyze this image."
        if user_statement:
            prompt_text += f"\nUser statement about this image: {user_statement}"

        semantic_description = ""
        try:
            response = client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    },
                ],
                temperature=0.1,
                max_completion_tokens=600,
            )
            content = getattr(response.choices[0].message, "content", None)
            semantic_description = str(content or "").strip()
        except Exception as exc:
            logger.warning(f"Groq vision analysis error: {exc}")
            semantic_description = (
                f"Visual content analysis encountered an error: {str(exc)}"
            )

        if user_statement and semantic_description:
            combined = f"User description: {user_statement}\nVisual analysis: {semantic_description}"
        elif user_statement:
            combined = user_statement
        else:
            combined = semantic_description or "Uploaded image evidence."

        return semantic_description, combined

    def analyze_document(
        self,
        *,
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
        user_description: Optional[str] = None,
    ) -> Tuple[str, str]:
        user_statement = (user_description or "").strip()
        extracted_text = ""

        if mime_type == "application/pdf":
            try:
                import pypdf

                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                pages_text = []
                for idx, page in enumerate(reader.pages[:10]):  # First 10 pages max
                    txt = page.extract_text() or ""
                    if txt.strip():
                        pages_text.append(f"--- Page {idx + 1} ---\n{txt.strip()}")
                extracted_text = "\n\n".join(pages_text).strip()
            except Exception as exc:
                logger.warning(f"PDF extraction error: {exc}")
                extracted_text = f"PDF text extraction failed: {str(exc)}"
        else:
            # Plain text or code file
            try:
                extracted_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    extracted_text = file_bytes.decode("latin-1")
                except Exception as exc:
                    extracted_text = f"Binary/unparseable content ({str(exc)})"

        # Cap text for summary
        capped_text = extracted_text[:4000]

        # Summarize via LLM if text is substantial
        semantic_description = ""
        client = self._get_client()
        if len(capped_text.strip()) > 50 and client:
            try:
                response = client.chat.completions.create(
                    model=self.text_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Summarize the key information in this uploaded document/code file "
                                "for technical context. Highlight any errors, configurations, functions, "
                                "or critical data."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Filename: {original_filename}\nContent:\n{capped_text}",
                        },
                    ],
                    temperature=0.1,
                    max_completion_tokens=400,
                )
                content = getattr(response.choices[0].message, "content", None)
                semantic_description = str(content or "").strip()
            except Exception as exc:
                logger.warning(f"Document summarization error: {exc}")
                semantic_description = f"Document content from {original_filename}:\n{capped_text[:500]}"
        else:
            semantic_description = (
                f"Document content ({original_filename}): {capped_text[:300]}"
                if capped_text
                else f"Uploaded document {original_filename}"
            )

        if user_statement:
            combined = f"User description: {user_statement}\nDocument analysis: {semantic_description}"
        else:
            combined = semantic_description

        return semantic_description, combined

    def process_evidence(
        self,
        *,
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
        user_description: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        # Validate size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise ValueError(
                f"File size ({len(file_bytes)} bytes) exceeds limit of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        lower_mime = mime_type.lower()
        if lower_mime in ALLOWED_IMAGE_MIMES:
            kind = "image"
            semantic_desc, combined = self.analyze_image(
                file_bytes=file_bytes,
                mime_type=lower_mime,
                user_description=user_description,
            )
        elif lower_mime in ALLOWED_DOC_MIMES:
            kind = "document"
            semantic_desc, combined = self.analyze_document(
                file_bytes=file_bytes,
                original_filename=original_filename,
                mime_type=lower_mime,
                user_description=user_description,
            )
        elif (
            lower_mime in ALLOWED_TEXT_MIMES
            or lower_mime.startswith("text/")
            or original_filename.endswith(
                (
                    ".py",
                    ".ts",
                    ".tsx",
                    ".js",
                    ".jsx",
                    ".json",
                    ".sql",
                    ".log",
                    ".md",
                    ".txt",
                    ".env",
                    ".yaml",
                    ".yml",
                )
            )
        ):
            kind = "code" if any(original_filename.endswith(ext) for ext in [".py", ".ts", ".tsx", ".js", ".jsx", ".sql"]) else "text"
            semantic_desc, combined = self.analyze_document(
                file_bytes=file_bytes,
                original_filename=original_filename,
                mime_type=lower_mime,
                user_description=user_description,
            )
        else:
            kind = "file"
            user_statement = (user_description or "").strip()
            semantic_desc = f"Binary file: {original_filename} ({lower_mime})"
            combined = (
                f"{user_statement} (Attachment: {original_filename})"
                if user_statement
                else semantic_desc
            )

        return kind, semantic_desc, combined
