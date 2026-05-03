# Academic Network: Data Pipeline, Machine Learning & Serverless API

[![React](https://img.shields.io/badge/Frontend-React%20%2B%20TS-61DAFB?style=for-the-badge&logo=react&logoColor=black)]()
[![Django](https://img.shields.io/badge/Backend-Django%20REST-092E20?style=for-the-badge&logo=django&logoColor=green)]()
[![AWS](https://img.shields.io/badge/Cloud-AWS%20Lambda-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white)]()
[![Prefect](https://img.shields.io/badge/Pipeline-Prefect-0052FF?style=for-the-badge&logo=prefect&logoColor=white)]()
[![HuggingFace](https://img.shields.io/badge/ML-HuggingFace-3B4252?style=for-the-badge&logo=huggingface&logoColor=yellow)]()

**Part of the Academic Collaboration Network Dashboard Project**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Available-success)](https://academic-dashboard.thara-sritharadol.com)

This repository is a monorepo containing the complete end-to-end ecosystem for the Academic Collaboration Network project. It handles everything from offline **Data Engineering** and **Machine Learning** pipelines (processing over 4,600 academic papers) to serving a production-ready **Serverless Web API**.

## System Architecture

The project adopts a modern, hybrid-cloud architecture designed for scalability and cost-efficiency:

- **Frontend Interface:** React + TypeScript, hosted and automatically deployed via **Vercel** (`academic-dashboard.thara-sritharadol.com`).
- **Serverless Backend API:** Django REST Framework deployed as Serverless Functions using **AWS Lambda** and **API Gateway**.
- **Production Database:** Serverless PostgreSQL database hosted on **NeonDB**.
- **CI/CD Pipeline:** Fully automated deployments using **GitHub Actions**, secured with Secretless **OpenID Connect (OIDC)** authentication to AWS.
- **Data Lake / Storage:** **Amazon S3** is utilized for backing up intermediate pipeline data, laying the groundwork for a future full-cloud pipeline migration.

## Data Engineering & ML Pipeline (Prefect)

The offline ETL and ML pipeline is orchestrated locally using **Prefect**. Every task in the workflow passes data exclusively via **JSON** files, and results are systematically backed up to **Amazon S3** with distinct prefixes (`raw_zone`, `clean_zone`, etc.) for data lake management.

**Workflow Tasks:**

1.  **`tu_sync_authors` & `fetch_papers` (Extract):**
    - Fetches raw publication data and author metadata from academic databases (e.g., OpenAlex).
    - _S3 Backup Prefix:_ `raw_zone/`
2.  **`process_clean_papers` (Transform):**
    - Cleans and standardizes text data (Titles and Abstracts) using **SpaCy** for tokenization, lemmatization, and stop-word removal.
    - _S3 Backup Prefix:_ `clean_zone/`
3.  **`process_deduplicate` (Transform):**
    - Removes redundant academic entries to ensure data integrity.
    - _S3 Backup Prefix:_ `dedupe-zone/`
4.  **`process_cluster` (Machine Learning):**
    - Explores and compares multiple algorithms including **BERTopic**, **LDA (Latent Dirichlet Allocation)**, and **NMF**.
    - Discovers hidden thematic structures and assigns primary/secondary topic domains to papers and authors.
    - Utilizes **LLM (Gemini)** to automatically generate human-readable names for topic domains based on keywords.
    - _S3 Backup Prefix:_ `results-zone/`
5.  **`load_to_db` (Load):**
    - Maps the finalized JSON clustered data into relational database models and pushes it to the remote **NeonDB (PostgreSQL)** instance for the production API.

## Tech Stack & Libraries

- **Languages:** Python 3.10+, TypeScript
- **Web Framework:** Django, Django REST Framework, React
- **Cloud & DevOps:** AWS (Lambda, API Gateway, S3, IAM OIDC), Vercel, GitHub Actions, AWS SAM CLI
- **Pipeline Orchestration:** Prefect
- **Data Manipulation & S3:** `pandas`, `numpy`, `boto3`
- **Natural Language Processing:** `spacy`, `nltk`
- **Machine Learning:** `bertopic`, `scikit-learn`, `pyLDAvis`
- **Database:** `psycopg2-binary`, `SQLAlchemy`, `dj-database-url`

## Author

Developed as a Senior Project focusing on Data Engineering, Machine Learning (Topic Modeling), and modern Serverless Cloud Architecture.

## Screenshots

<img width="1920" height="1080" alt="Dashboard Overview" src="https://github.com/user-attachments/assets/64b180c9-a4b2-4879-a966-ee220381f283" />
<img width="1920" height="1080" alt="Topic Clustering View" src="https://github.com/user-attachments/assets/0a067203-2b21-42cc-bb9b-b87623bfa765" />
<img width="1920" height="1080" alt="Network Graph" src="https://github.com/user-attachments/assets/8942eea2-3ac2-4528-97cf-3afb5b8d654b" />
<img width="1920" height="1080" alt="Researcher Profile" src="https://github.com/user-attachments/assets/e79779ec-46d2-4142-b702-88d8ffdee03d" />
<img width="1920" height="1080" alt="Analytics View" src="https://github.com/user-attachments/assets/73609edb-dad0-4887-876f-9f4b9f520da7" />
