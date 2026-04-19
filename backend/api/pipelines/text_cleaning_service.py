import re

class TextCleaningService:

    @staticmethod
    def clean_html_xml_tags(text: str) -> str:
        if not text:
            return ""
            
        cleaned_text = re.sub(r'<.*?>', ' ', text)
        cleaned_text = re.sub(r'[^\x00-\x7F]+', ' ', cleaned_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        cleaned_text = re.sub(r'\s+([.,;:?!])', r'\1', cleaned_text)
        
        return cleaned_text