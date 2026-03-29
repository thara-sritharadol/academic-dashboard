import pytest
from api.services.text_cleaning_service import TextCleaningService

def test_clean_html_xml_tags_normal_html():
    text = "<p>This is an <b>Abstract</b>.</p>"
    expected = "This is an Abstract."
    assert TextCleaningService.clean_html_xml_tags(text) == expected

def test_clean_html_xml_tags_extra_spaces():
    text = "   Here   <br>   is   text.  "
    expected = "Here is text."
    assert TextCleaningService.clean_html_xml_tags(text) == expected

def test_clean_html_xml_tags_empty_or_none():
    # Edge Cases
    assert TextCleaningService.clean_html_xml_tags("") == ""
    assert TextCleaningService.clean_html_xml_tags(None) == ""