import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from nltk.tokenize import sent_tokenize
import nltk


from api.models import Paper, SkillEmbedding, ExtractedSubSkill

class SubSkillClassifier:
    
    def __init__(self, model_name: str, source: str):
        self.stdout = lambda x: print(x)
        self.stdout(f"NLTK: Loading 'punkt' tokenizer...")
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab')
        
        self.stdout(f"Loading Model '{model_name}' ...")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        
        #Load Skill Embeddings from Database
        self.skill_list, self.skill_embeddings = self._load_skill_embeddings(model_name, source)

    def _load_skill_embeddings(self, model_name: str, source: str):
        """
        Load all Skill Embeddings that match with source and model
        """
        self.stdout(f"Loading Skill Embeddings from DB (source='{source}', model='{model_name}')...")
        
        skills = SkillEmbedding.objects.filter(model_name=model_name, source=source)
        
        if not skills.exists():
            raise ValueError(f"Not Found SkillEmbedding for (source='{source}', model='{model_name}')")
            
        #create skill list
        skill_list = [t.skill_name for t in skills]
        emb_list = [np.frombuffer(t.embedding, dtype=np.float32) for t in skills]
        
        #Stack
        skill_embeddings_tensor = torch.tensor(np.vstack(emb_list), device=self.model.device)
        
        self.stdout(f"Loading successfully {len(skill_list):,} skills.\n")
        return skill_list, skill_embeddings_tensor

    def classify_paper_sentences(self, paper: Paper, confidence_threshold=0.45):
        """
        Process 1 Paper:
        1. Divide sentences
        2. Classify every sentence against every skill
        3. Filter by Threshold
        4. Save Sub-Skills to Database
        """
        
        #Prepare text and divide sentences.
        title = paper.title.strip() if paper.title else ""
        abstract = paper.abstract.strip() if paper.abstract else ""
        
        full_text = f"{title}. {abstract}".strip()
        
        if not full_text:
            return 0

        sentences = sent_tokenize(full_text)
        
        if not sentences:
            return 0
            
        #Encode entire sentences at once
        sentence_embs = self.model.encode(
            sentences, 
            convert_to_tensor=True, 
            normalize_embeddings=True,
            show_progress_bar=False #use tqdm instent
        )
        
        #Calculate Similarity Matrix
        #The result is a matrix of size [number of sentences x number of skills].
        cos_matrix = util.cos_sim(sentence_embs, self.skill_embeddings)
        
        #Find the highest value (Top-1) of each sentence.
        #top_results.values is [score], top_results.indices is [index]
        top_results = torch.topk(cos_matrix, k=1, dim=1)
        
        top_scores = top_results.values.cpu().numpy()[:, 0]
        top_indices = top_results.indices.cpu().numpy()[:, 0]

        #Prepare to save to the database
        objs_to_create = []
        for i, sentence in enumerate(sentences):
            score = float(top_scores[i])
            
            #Filter out sub-skill that are not confident about (low score)
            if score < confidence_threshold:
                continue
                
            skill_index = top_indices[i]
            skill_name = self.skill_list[skill_index]
            
            objs_to_create.append(
                ExtractedSubSkill(
                    paper=paper,
                    skill_name=skill_name,
                    confidence=score,
                    source_sentence=sentence,
                    embedding_model=self.model_name
                )
            )
            
        #Save SubSkill to database
        if objs_to_create:
            ExtractedSubSkill.objects.bulk_create(objs_to_create, ignore_conflicts=True)
            
        return len(objs_to_create)