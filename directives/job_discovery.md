# Job Discovery Workflow

**Directive Type:** Core Workflow
**Owner:** JobFlow System
**Last Updated:** 2026-01-31
**Status:** Active

---

## Purpose

Discover, collect, and normalize job postings from various sources to build a comprehensive and up-to-date job database.

This workflow ensures that:
- Job postings are collected systematically from multiple sources
- Data is standardized into a consistent format
- Duplicates are identified and eliminated
- Only high-quality, complete job postings enter the system
- The job database stays current and accurate

---

## Inputs

The job discovery workflow accepts the following inputs:

### Primary Input: Raw Job Posting Data

A dictionary or JSON object containing job posting information with any of the following fields:

**Required fields (at least one must be present):**
- Job title (may be named: `title`, `job_title`, `position`)
- Company name (may be named: `company`, `employer`, `company_name`)

**Optional fields:**
- Location (may be named: `location`, `loc`, `city`)
- Job description (may be named: `description`, `desc`, `job_description`)
- Requirements/qualifications (may be string or list)
- Salary information (min/max, may be nested or separate fields)
- Posted date (ISO format preferred)
- Original posting URL

**Source variations:**
Different job boards and APIs provide data in different formats. This workflow must handle variability in field names, data types, and structures.

---

## High-Level Steps

The job discovery workflow consists of four sequential stages:

### 1. Fetch Job Sources
**What:** Retrieve raw job posting data from configured sources
**Sources may include:**
- Job board APIs (Indeed, LinkedIn, Glassdoor, etc.)
- Company career pages
- RSS feeds
- Uploaded files (CSV, JSON)
- Manual entries

**Outcome:** Raw job posting data collected from one or more sources

---

### 2. Parse and Normalize Job Postings
**What:** Transform raw job data into a consistent, standardized format
**Actions:**
- Map various field names to standard schema
- Convert data types (e.g., salary strings to numbers)
- Extract structured data from unstructured text where needed
- Clean and trim whitespace
- Validate required fields are present

**Outcome:** Normalized job posting records with consistent field names and types

---

### 3. Deduplicate Jobs
**What:** Identify and remove duplicate job postings
**Deduplication criteria:**
- Same job title + same company + same location = likely duplicate
- Check posting URL if available (exact match = definite duplicate)
- Consider posting dates (newer posting wins)

**Outcome:** Unique job postings only, duplicates removed or merged

---

### 4. Store Jobs
**What:** Persist validated, deduplicated job postings to the database
**Actions:**
- Insert new job postings
- Update existing postings if more recent data available
- Record metadata (source, discovery date, last updated)
- Maintain audit trail

**Outcome:** Job postings successfully stored in database and ready for matching

---

## Constraints and Rules

### Data Quality Rules

**Minimum Quality Bar:**
- Every job posting MUST have a title
- Every job posting MUST have a company name
- If location is missing, default to "Not Specified" (do not reject)
- If description is missing, the posting is considered low quality but not rejected

**Data Validation:**
- Salary values must be positive numbers (if present)
- Dates must be valid ISO format or parseable date strings
- URLs must be valid HTTP/HTTPS URLs (if present)
- Requirements must be extractable as a list of discrete items

### Deduplication Rules

**When two postings match:**
- Keep the one with more complete information
- If completeness is equal, keep the more recent one
- If dates are equal, keep the first one encountered
- Never silently overwrite without checking

**Duplicate detection:**
- Case-insensitive comparison for title, company, location
- Normalize company names (e.g., "Google Inc." = "Google")
- Consider "Remote" = "Remote, USA" = "Work from Home" as equivalent locations

### Processing Rules

**Error Handling:**
- Individual job posting failures should not halt the entire workflow
- Log all failures with source information for debugging
- Continue processing remaining jobs
- Report summary of successes and failures at end

**Idempotency:**
- Running the same input twice should not create duplicates
- Use URL or (title + company + location) as idempotency key
- Safe to rerun the workflow on the same data

**Rate Limits:**
- Respect source API rate limits (if applicable)
- Throttle requests to avoid overwhelming external services
- Implement exponential backoff on failures

---

## Success Criteria

The job discovery workflow is successful when:

1. **Completeness**
   - All accessible job sources were queried
   - At least 90% of discovered postings were successfully processed
   - Failed postings are logged with clear error messages

2. **Data Quality**
   - All stored jobs have required fields (title, company)
   - Data is normalized to consistent format
   - Salary and date fields are properly typed (not strings)

3. **Uniqueness**
   - No duplicate job postings exist in the database
   - Each unique job appears exactly once
   - Deduplication logic was applied correctly

4. **Auditability**
   - Source of each job posting is recorded
   - Discovery timestamp is captured
   - Processing metadata is available for debugging

5. **Performance**
   - Workflow completes in reasonable time (target: <5 minutes for 1000 jobs)
   - No memory leaks or resource exhaustion
   - Database writes are batched efficiently

---

## Failure Scenarios

### When to Alert

**Critical failures (halt workflow):**
- Database is unreachable
- All job sources fail simultaneously
- Data corruption detected

**Non-critical failures (log and continue):**
- Individual job source is down
- Single job posting is malformed
- Deduplication logic encounters edge case

### Recovery Procedures

**If the workflow fails mid-execution:**
- Identify the last successful step
- Resume from that point (do not restart from beginning)
- Use transaction boundaries to ensure atomicity where appropriate

**If data quality issues are detected:**
- Flag affected jobs for manual review
- Do not automatically reject (humans should decide)
- Generate data quality report for investigation

---

## Edge Cases

### Unusual but Valid Scenarios

1. **Job posting with no location**
   - Accept and mark location as "Not Specified"
   - Still attempt to match with candidates

2. **Extremely high or low salary**
   - Accept but flag for review
   - May indicate data quality issue or unusual role

3. **Very old posting date**
   - Accept if source confirms it's still active
   - May indicate long-running open position

4. **Missing URL**
   - Still process if other fields are complete
   - Generate placeholder or use company careers page

### Known Limitations

- Cannot parse jobs from sources requiring authentication (unless credentials provided)
- May miss jobs that are not publicly listed
- Deduplication may not catch all variants of same job
- Quality of normalization depends on quality of source data

---

## Future Enhancements

**Not in scope for current implementation, but planned:**

1. **AI-powered parsing** for unstructured job descriptions
2. **Automatic skill extraction** from job requirements
3. **Salary estimation** for postings without salary data
4. **Geographic normalization** (e.g., city → state → country hierarchy)
5. **Company metadata enrichment** (size, industry, funding)

---

## Related Documents

- **Pipeline:** `/pipelines/job_discovery.py` (workflow structure definition)
- **Execution:** `/execution/normalize_job_posting.py` (normalization logic)
- **Orchestrator:** `jobflow/app/core/orchestrator.py` (current implementation)

---

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2026-01-31 | 1.0 | Initial directive created | System |

---

**Note:** This directive describes *what* the job discovery workflow should accomplish and *why*. It does not prescribe *how* to implement it. Implementation details belong in execution scripts and pipeline definitions.
