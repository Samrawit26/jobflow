# Core Business Logic

Core business logic and domain rules.

Responsible for:
- Business rule enforcement
- Domain logic
- Application-specific algorithms
- Cross-cutting concerns

## Modules

### candidate_intake.py
Converts candidate-provided application sheets (Excel) into normalized profiles for matching/submission. Parses personal information and skills from the "Application Info.xlsx" template with resilience to blank rows and section headers.

### job_model.py
Canonical job posting domain model used across aggregation, matching, approvals, and execution pipelines. Normalizes messy job data from various sources into consistent structure with deterministic fingerprinting.

### job_source.py
Protocol interface for pluggable job feed sources. Defines contract for fetching raw job dicts that are normalized elsewhere.

### job_aggregator.py
Multi-source job aggregator with fingerprint-based deduplication. Orchestrates fetching from multiple JobSource implementations, normalizes raw data, and maintains stable ordering.

### file_job_source.py
File-based JobSource implementation for local fixtures and exports. Reads job postings from JSON files for testing and offline scenarios.

### search_query.py
Search query builder that transforms candidate profiles into structured job search queries. Maps candidate preferences and skills to search criteria. (Legacy - use candidate_query_builder.py for new code)

### candidate_profile.py
Canonical candidate profile domain model. Normalizes messy candidate data into consistent structure with defensive field handling and flexible key name support.

### candidate_query_builder.py
Intelligent candidate-to-query builder with title inference and keyword extraction. Automatically infers job titles from skill patterns (Power BI, Python backend, Data Engineering) and extracts keywords from skills and resume text.

### match_result.py
Frozen dataclass for candidate-job match results with validation. Contains overall score (0-100), decision (strong_fit/possible_fit/weak_fit/reject), dimension scores, explainable reasons, matched/missing keywords, and metadata. Validates score bounds and decision-threshold alignment.

### job_matcher.py
Deterministic candidate-to-job matching engine with dimension-based scoring. Computes skills overlap (45%), title alignment (25%), location alignment (15%), and seniority alignment (15%) to produce weighted overall score with explainable reasons. Normalizes keywords, extracts technical terms, and generates stable match results.

### candidate_folder_loader.py
Candidate folder ingestion loader. Loads complete candidate profiles from local folders containing application info (XLSX) and resume files. Orchestrates parsing, merges skills from application and resume, and produces normalized CandidateProfile instances for job discovery pipeline.

### resume_parser.py
Resume text extraction and skill detection (stdlib only). Extracts text from .txt, .md, and .docx files (no .doc support). Deterministic skill extraction using built-in keyword dictionary and pattern matching for technical terms and acronyms.

### xlsx_kv_reader.py
XLSX key-value reader using stdlib only. Reads application info spreadsheets with column A = keys, column B = values. Parses XLSX as ZIP with XML using zipfile and ElementTree. Handles shared strings and numeric values.
