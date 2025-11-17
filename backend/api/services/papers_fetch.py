import requests
import time

def _enrich_with_semantic_scholar(doi: str) -> dict:
    
    #Fetches additional paper details from Semantic Scholar using a DOI.

    if not doi:
        return {}

    s2_url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    s2_params = {"fields": "abstract,fieldsOfStudy,citationCount"}
    
    try:
        s2_resp = requests.get(s2_url, params=s2_params, timeout=10)
        if s2_resp.status_code == 200:
            s2_data = s2_resp.json()
            return {
                "abstract": s2_data.get("abstract"),
                "fields_of_study": ",".join(s2_data.get("fieldsOfStudy", []) or []),
                "citation_count": s2_data.get("citationCount", 0),
            }
    except requests.RequestException:
        #Handle cases where the API is down or there's a network issue
        pass
        
    return {}

def stream_papers_from_apis(author: str = None, query: str = None, start_year: int = None, end_year: int = None):
    """
    A generator that fetches papers from the CrossRef API, enriches them with
    Semantic Scholar data, and yields the total count first, then each paper's data.
    """
    url = "https://api.crossref.org/works"
    rows_per_page = 1000
    offset = 0
    target_author = author.lower().strip() if author else None

    #Setup Query Parameters
    base_params = {"rows": rows_per_page}
    if start_year and end_year:
        base_params["filter"] = f"from-pub-date:{start_year},until-pub-date:{end_year}"
    if author:
        base_params["query.author"] = author
    if query:
        base_params["query"] = query
    
    #First API call to get total results
    try:
        first_resp = requests.get(url, params={**base_params, "offset": 0}, timeout=10)
        if first_resp.status_code != 200:
            #If the first call fails, we can't proceed.
            yield 0 #Yield 0 to indicate no results
            return
        
        total_results = first_resp.json().get("message", {}).get("total-results", 0)
        yield total_results #First, yield the total count for the progress bar
        
        if total_results == 0:
            return
            
    except requests.RequestException:
        yield 0
        return

    time.sleep(1)

    #Main Pagination Loop
    while offset < total_results:
        params = base_params.copy()
        params["offset"] = offset

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                break #Exit loop on subsequent errors
            
            items = response.json().get("message", {}).get("items", [])
            if not items:
                break #No more items, exit
        except requests.RequestException:
            break

        for item in items:
            #Author Matching Logic
            item_authors = item.get("author", [])
            if target_author:
                match_found = any(
                    f"{a.get('given', '')} {a.get('family', '')}".strip().lower() == target_author
                    for a in item_authors
                )
                if not match_found:
                    continue #Skip this paper if no author matches

            #Parse CrossRef Data
            doi = item.get("DOI")
            title = " ".join(item.get("title", [])) or "(No Title)"
            
            year = None
            if "published-print" in item:
                year = item["published-print"]["date-parts"][0][0]
            elif "published-online" in item:
                year = item["published-online"]["date-parts"][0][0]

            authors_list = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in item_authors]

            paper_data = {
                "doi": doi,
                "title": title,
                "authors": ", ".join(authors_list),
                "year": year,
                "venue": (item.get("container-title") or [None])[0],
                "url": item.get("URL"),
            }

            #Enrich with Semantic Scholar
            enriched_data = _enrich_with_semantic_scholar(doi)
            paper_data.update(enriched_data)

            yield paper_data

        offset += rows_per_page
        time.sleep(1)