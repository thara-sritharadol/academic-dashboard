import requests
import time

POLITE_EMAIL = "thara.sri@dome.tu.ac.th"
S2_API_KEY = ""

def get_common_headers():
    headers = {
        "User-Agent": f"TU-Research-Network-Bot/1.0 (mailto:{POLITE_EMAIL})"
    }
    return headers

def _enrich_with_semantic_scholar(doi: str) -> dict:
    #Fetches additional paper details from Semantic Scholar using a DOI.
    if not doi:
        return {}

    s2_url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    s2_params = {"fields": "abstract,fieldsOfStudy,citationCount"}

    headers = get_common_headers()
    if S2_API_KEY:
        headers["x-api-key"] = S2_API_KEY
    
    for attempt in range(3):
        try:
            s2_resp = requests.get(s2_url, params=s2_params, headers=headers, timeout=10)
            if s2_resp.status_code == 200:
                s2_data = s2_resp.json()
                return {
                    "abstract": s2_data.get("abstract"),
                    "fields_of_study": ",".join(s2_data.get("fieldsOfStudy", []) or []),
                    "citation_count": s2_data.get("citationCount", 0),
                }
            elif s2_resp.status_code == 429: # Too Many Requests
                print(f"   > Semantic Scholar rate limit hit. Waiting 5 seconds... (Attempt {attempt+1})")
                time.sleep(5)
                continue
            else:
                break # Skip other errors.
        except requests.RequestException:
            time.sleep(2)
            
    return {}

def _get_openalex_author_id(author_name: str) -> str:
    url = "https://api.openalex.org/authors"
    params = {"search": author_name}
    try:
        resp = requests.get(url, params=params, headers=get_common_headers(),timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                found_name = results[0].get('display_name')
                found_id = results[0].get('id')
                print(f"   > OpenAlex resolved '{author_name}' to ID: {found_id} ({found_name})")
                return found_id
    except requests.RequestException:
        pass
    return None

def _reconstruct_openalex_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return None
    
    max_index = 0
    for positions in inverted_index.values():
        max_index = max(max_index, max(positions))
    
    text_list = [""] * (max_index + 1)
    
    for word, positions in inverted_index.items():
        for pos in positions:
            text_list[pos] = word
            
    return " ".join(text_list)

def _stream_from_openalex(author: str = None, query: str = None, start_year: int = None, end_year: int = None):
    base_url = "https://api.openalex.org/works"
    per_page = 50 
    
    params = {
        "per_page": per_page,
        "sort": "publication_date:desc"
    }
    
    api_filters = []
    
    if author:
        author_id = _get_openalex_author_id(author)
        if author_id:
            api_filters.append(f"author.id:{author_id}")
        else:
            print(f"   > Warning: Could not resolve Author ID for '{author}', trying raw text search.")
            api_filters.append(f"authorships.author.search:{author}")

    if start_year and end_year:
        api_filters.append(f"publication_year:{start_year}-{end_year}")
    
    if api_filters:
        params["filter"] = ",".join(api_filters)
        
    if query:
        params["search"] = query

    try:
        first_resp = requests.get(base_url, params=params, headers=get_common_headers(),timeout=10)
        if first_resp.status_code != 200:
            yield 0
            return
        
        data = first_resp.json()
        total_results = data.get("meta", {}).get("count", 0)
        yield total_results 
        
        if total_results == 0:
            return
    except requests.RequestException:
        yield 0
        return

    total_pages = (total_results // per_page) + 1
    
    for page in range(1, total_pages + 1):
        if (page * per_page) > 10000:
            break

        params["page"] = page
        
        try:
            resp = requests.get(base_url, params=params, headers=get_common_headers(), timeout=10)
            if resp.status_code != 200: 
                break
            
            items = resp.json().get("results", [])
            if not items: 
                break
                
            for item in items:
                doi_url = item.get("doi")
                doi = doi_url.replace("https://doi.org/", "") if doi_url else None
                
                if not doi: continue

                #1. Extract Authors with Metadata
                authorships = item.get("authorships", [])
                
                authors_struct = []

                authors_names = []
                
                for a in authorships:
                    auth_node = a.get("author", {})
                    name = auth_node.get("display_name", "")
                    oa_id = auth_node.get("id") # e.g., https://openalex.org/A1234...
                    
                    if name:
                        authors_names.append(name)
                        authors_struct.append({
                            "name": name,
                            "openalex_id": oa_id
                        })

                primary_loc = item.get("primary_location") or {}
                venue_source = primary_loc.get("source") or {}
                venue_name = venue_source.get("display_name")

                concepts = []
                for concept in item.get("concepts", []):
                     concept_id = concept.get("id") 
                     concept_name = concept.get("display_name")
                     concept_score = concept.get("score", 0.0)
                     concept_level = concept.get("level")
                     if concept_id and concept_name:
                         concepts.append({
                             "openalex_id": concept_id,
                             "name": concept_name,
                             "score": concept_score,
                             "level": concept_level,
                         })

                paper_data = {
                    "doi": doi,
                    "title": item.get("title", "(No Title)"),
                    "authors_text": ", ".join(authors_names),
                    "authors_struct": authors_struct,# Send a list of dictionaries to the command line for processing.
                    "year": item.get("publication_year"),
                    "venue": venue_name,
                    "url": doi_url,
                    "citation_count": item.get("cited_by_count", 0),
                    "openalex_concepts": concepts,
                }

                raw_abstract = item.get("abstract_inverted_index")
                openalex_abstract = _reconstruct_openalex_abstract(raw_abstract)

                paper_data["abstract"] = openalex_abstract
                
                yield paper_data
                
            time.sleep(0.5)
            
        except requests.RequestException:
            break

def _stream_from_crossref(author: str = None, query: str = None, start_year: int = None, end_year: int = None):

    url = "https://api.crossref.org/works"
    rows_per_page = 1000
    offset = 0
    target_author = author.lower().strip() if author else None

    base_params = {"rows": rows_per_page}
    if start_year and end_year:
        base_params["filter"] = f"from-pub-date:{start_year},until-pub-date:{end_year}"
    if author:
        base_params["query.author"] = author
    if query:
        base_params["query"] = query
    
    try:
        first_resp = requests.get(url, params={**base_params, "offset": 0}, headers=get_common_headers(),timeout=10)
        if first_resp.status_code != 200:
            yield 0
            return
        
        total_results = first_resp.json().get("message", {}).get("total-results", 0)
        yield total_results
        
        if total_results == 0:
            return
            
    except requests.RequestException:
        yield 0
        return

    time.sleep(1)

    while offset < total_results:
        params = base_params.copy()
        params["offset"] = offset

        try:
            response = requests.get(url, params=params, headers=get_common_headers(),timeout=10)
            if response.status_code != 200:
                break
            
            items = response.json().get("message", {}).get("items", [])
            if not items:
                break
        except requests.RequestException:
            break

        for item in items:
            item_authors = item.get("author", [])
            if target_author:
                match_found = any(
                    f"{a.get('given', '')} {a.get('family', '')}".strip().lower() == target_author
                    for a in item_authors
                )
                if not match_found:
                    continue

            doi = item.get("DOI")
            title = " ".join(item.get("title", [])) or "(No Title)"
            
            year = None
            if "published-print" in item:
                year = item["published-print"]["date-parts"][0][0]
            elif "published-online" in item:
                year = item["published-online"]["date-parts"][0][0]

            authors_struct = []
            authors_names = []
            for a in item_authors:
                full_name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                if full_name:
                    authors_names.append(full_name)
                    #CrossRef ไม่มี ID ของ OpenAlex ใส่ None ไว้
                    authors_struct.append({"name": full_name, "openalex_id": None})

            paper_data = {
                "doi": doi,
                "title": title,
                "authors_text": ", ".join(authors_names),
                "authors_struct": authors_struct,
                "year": year,
                "venue": (item.get("container-title") or [None])[0],
                "url": item.get("URL"),
            }

            enriched_data = _enrich_with_semantic_scholar(doi)
            paper_data.update(enriched_data)

            yield paper_data

        offset += rows_per_page
        time.sleep(0.7)

def stream_papers_from_apis(author: str = None, query: str = None, start_year: int = None, end_year: int = None, source: str = "openalex"):
    if source == "openalex":
        yield from _stream_from_openalex(author, query, start_year, end_year)
    else:
        yield from _stream_from_crossref(author, query, start_year, end_year)