# Academic Network: Data Pipeline & Machine Learning
[![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=green)]()
[![React](https://img.shields.io/badge/Tech-React%20%2B%20TypeScript-61DAFB?style=for-the-badge&logo=react&logoColor=black)]()
[![HuggingFace](https://img.shields.io/badge/-HuggingFace-3B4252?style=flat&logo=huggingface&logoColor=)]()

**Part of the Academic Collaboration Network Dashboard Project**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Available-success)](https://https://academic-dashboard-api.vercel.app/)
[![Web API Repo](https://img.shields.io/badge/API%20Repo-View%20Source-blue)](https://github.com/thara-sritharadol/academic-dashboard-api)
This repository contains the offline **Data Engineering** and **Machine Learning** pipeline for the Academic Collaboration Network project. It is responsible for extracting, processing, and clustering over 4,600 academic research papers, ultimately structuring the data for the production Web API.

## Pipeline Workflow (ETL & ML)

1. **Extract (Data Collection):** * Fetches raw publication data and author metadata (e.g., via OpenAlex or other academic databases).
2. **Transform (Text Preprocessing):** * Cleans and standardizes text data (Titles and Abstracts).
   * Utilizes **SpaCy** for tokenization, lemmatization, and stop-word removal.
3. **Machine Learning (Topic Modeling):** * Explores and compares multiple clustering algorithms including **BERTopic**, **LDA (Latent Dirichlet Allocation)**, and **NMF (Non-negative Matrix Factorization)** to discover hidden thematic structures within the papers.
   * Assigns primary and secondary topic domains to each paper and author.
   * Naming topic domains using keywords via **LLM (Gemini)**.
4. **Load (Database Seeding):** * Maps the clustered data into relational database models.
   * Automatically pushes the structured data to a remote **PostgreSQL** instance (Neon.tech) for production use.

## Tech Stack & Libraries

* **Language:** Python 3.10+
* **Data Manipulation:** `pandas`, `numpy`
* **Natural Language Processing:** `spacy`, `nltk`
* **Machine Learning / Clustering:** `bertopic`, `scikit-learn` (`pyLDAvis` for visualization)
* **Database Connection:** `psycopg2-binary`, `SQLAlchemy`
* **Environment Management:** `python-dotenv`

## How to Run the Pipeline Locally

Since this repository contains heavy ML models and dependencies, it is recommended to run this within a dedicated virtual environment.

**1. Clone and Setup Environment**
```bash
git clone https://github.com/thara-sritharadol/academic-dashboard.git
cd senior-project-ml-pipeline
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```
**2. Install Dependencies**
```bash
# This will install heavy libraries like torch, spacy, and bertopic
pip install -r requirements.txt

# Download SpaCy English model
python -m spacy download en_core_web_sm
```
**3. Environment Variables**

Create a .env file in the root directory to connect to the target database:
```
DATABASE_URL=postgresql://<user>:<password>@<your-neon-host>/<db-name>?sslmode=require
```
**4. Execute the Pipeline**

*(Note: Update the command below based on your actual script name)*

```
# Example: Run the full ETL and clustering process
python run_pipeline.py
```

## Author
Developed as a Senior Project focusing on Data Science, Topic Modeling, and Backend Architecture.

## Screenshot
<img width="1920" height="1080" alt="Screenshot (394)" src="https://github.com/user-attachments/assets/64b180c9-a4b2-4879-a966-ee220381f283" />
<img width="1920" height="1080" alt="Screenshot (395)" src="https://github.com/user-attachments/assets/0a067203-2b21-42cc-bb9b-b87623bfa765" />
<img width="1920" height="1080" alt="Screenshot (397)" src="https://github.com/user-attachments/assets/8942eea2-3ac2-4528-97cf-3afb5b8d654b" />
<img width="1920" height="1080" alt="Screenshot (398)" src="https://github.com/user-attachments/assets/e79779ec-46d2-4142-b702-88d8ffdee03d" />
<img width="1920" height="1080" alt="Screenshot (399)" src="https://github.com/user-attachments/assets/73609edb-dad0-4887-876f-9f4b9f520da7" />

## Evaluation
### LDA
<img width="3000" height="1800" alt="lda_optimal_k_selection_s1" src="https://github.com/user-attachments/assets/2b3d43e3-c019-4362-9bf9-daa76ea39170" />
<img width="2400" height="1800" alt="lda_s1_k4_heatmap_l0" src="https://github.com/user-attachments/assets/6d1b39d2-d18a-4951-ad13-9131709a6dde" />
<img width="4500" height="2400" alt="lda_barchart_s1_k4" src="https://github.com/user-attachments/assets/342afc6b-fc3a-4cf1-a893-4ee72761247a" />

### NMF
<img width="3000" height="1800" alt="nmf_optimal_k_selection_s1" src="https://github.com/user-attachments/assets/2d80d498-ee63-43fc-b214-6e8ba542c214" />
<img width="2400" height="1800" alt="nmf_s1_k5_heatmap_l0" src="https://github.com/user-attachments/assets/fd274f4b-84c2-4c38-9e0e-864a73c81b91" />
<img width="4500" height="2400" alt="nmf_barchart_s1_k5" src="https://github.com/user-attachments/assets/4078c4fc-fe1b-4234-a72b-60cfc300d58f" />

### BERTopic
<img width="2400" height="1800" alt="bertopic_s1_k_approx_heatmap_l0" src="https://github.com/user-attachments/assets/c312e0dd-29db-4585-9c5a-a5ab47ac515e" />
<img width="4500" height="4800" alt="bertopic_barchart_s1_k_approx" src="https://github.com/user-attachments/assets/62fcd080-b71c-4445-9f25-e58077edba3c" />





