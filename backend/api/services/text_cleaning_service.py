import re

class TextCleaningService:

    @staticmethod
    def clean_html_xml_tags(text: str) -> str:
        if not text:
            return ""
            
        # Delete HTML/XML tags
        cleaned_text = re.sub(r'<.*?>', ' ', text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        cleaned_text = re.sub(r'\s+([.,;:?!])', r'\1', cleaned_text)
        
        return cleaned_text