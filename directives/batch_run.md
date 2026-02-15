# Batch Candidate Processing

**Directive Type:** Batch Operations
**Owner:** JobFlow System
**Last Updated:** 2026-02-01
**Status:** Active

---

## Purpose

Process multiple candidate folders in batch to discover, aggregate, and match job opportunities for each candidate.

This workflow ensures that:
- All candidate folders in a directory are processed systematically
- Each candidate's profile is loaded from their application info and resume
- Jobs are aggregated from specified sources for each candidate
- Match scores are computed to rank job opportunities
- Results are written to structured output files for review
- Processing errors are captured without halting the batch

---

## Inputs

The batch candidate processing workflow requires the following inputs:

### Required Inputs

**candidates_dir** (string)
- Path to directory containing candidate folders
- Each subfolder must contain:
  - One `.xlsx` file with application info (key-value pairs)
  - One resume file (`.txt`, `.md`, or `.docx`)
- Folders without these files are skipped

**jobs** (string)
- Path to JSON file containing job postings
- Used as data source for job aggregation
- Format: list of job dicts or `{"jobs": [...]}`

**out** (string)
- Path to output directory for results
- Will be created if it doesn't exist
- All output files are written here

### Optional Inputs

**match_jobs** (boolean, default: true)
- Whether to compute match scores for each candidate-job pair
- If false, only job aggregation is performed

---

## High-Level Steps

1. **Discover Candidate Folders**
   - Scan candidates_dir for subdirectories
   - Filter to folders containing .xlsx and resume files
   - Sort alphabetically for deterministic processing

2. **Process Each Candidate**
   - Load candidate profile from folder (application + resume)
   - Build search query from candidate profile
   - Aggregate jobs from job sources
   - (Optional) Compute match scores and rank jobs
   - Write per-candidate results to `<out>/results/<candidate_id>/results.json`
   - Capture any errors without halting batch

3. **Generate Batch Summary**
   - Write `<out>/summary.csv` with key metrics for all candidates
   - Write `<out>/errors.json` with any processing failures
   - Return summary dict with counts and file paths

---

## Outputs

### Primary Outputs

**summary.csv**
- Location: `<out>/summary.csv`
- Format: CSV with headers
- Columns: candidate_id, folder, num_jobs, num_matches, top_score, num_errors, status
- One row per candidate processed

**Per-Candidate Results**
- Location: `<out>/results/<candidate_id>/results.json`
- Format: JSON with complete job discovery pipeline output
- Contains: candidate profile, jobs, matches (if enabled), query, counts

**errors.json**
- Location: `<out>/errors.json`
- Format: JSON array of error objects
- Each error contains: folder, error_type, error_message, traceback

---

## Safety & Constraints

### File System Access
- **Reads**: candidates_dir (candidate folders), jobs file
- **Writes**: All outputs restricted to out_dir
- **No modifications**: Input directories and files are never modified

### Data Privacy
- Candidate data is read from local files only
- No network calls or external API requests
- All processing is local and deterministic
- Output files contain full candidate profiles (treat as sensitive)

### Error Handling
- Individual candidate failures are captured, not raised
- Batch continues processing remaining candidates after errors
- All errors are logged to errors.json with stack traces
- Failed candidates appear in summary.csv with status="failed"

---

## Risks

**Risk: Writing Output Files**
- Severity: Low
- Mitigation: All writes confined to user-specified out_dir
- Approval: Required

**Risk: Reading Candidate PII**
- Severity: Medium
- Description: Processes candidate resumes and application data
- Mitigation: No data transmitted externally, local processing only
- Approval: Required

**Risk: Large Output Size**
- Severity: Low
- Description: Per-candidate results can be large with many jobs
- Mitigation: User specifies out_dir with sufficient space
- Approval: Required

---

## Approval Requirements

This workflow requires explicit approval before execution because it:
1. Reads candidate personal information (PII) from local files
2. Writes output files to the filesystem
3. Processes potentially sensitive employment data

Approval must include:
- Verification that candidates_dir path is correct
- Confirmation that out_dir location is appropriate
- Acknowledgment that output files will contain candidate PII

---

## Example Usage

### Payload Format

```json
{
  "candidates_dir": "./data/candidates",
  "jobs": "./data/jobs.json",
  "out": "./results/batch_2026_02_01",
  "match_jobs": true
}
```

### Expected Behavior

Given 3 candidate folders (alice, bob, charlie) and 10 jobs:
- Processes all 3 candidates
- Writes 3 result files: results/alice/results.json, results/bob/results.json, results/charlie/results.json
- Generates summary.csv with 3 rows
- If matching enabled, ranks jobs by score for each candidate
- Completes in deterministic manner (same inputs → same outputs)

---

## Related Workflows

- **job_discovery**: Single-candidate job discovery (called internally)
- **candidate_intake**: Parse candidate application files
- **job_matching**: Compute candidate-job match scores
