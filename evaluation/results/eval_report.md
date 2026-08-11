# Evaluation Report

**Generated:** 2026-08-10 09:20:44  
**Ground Truth Size:** 300 Q&A pairs

## Retrieval Evaluation

| Strategy | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@1 | MRR@3 | MRR@5 | MRR@10 |
|---|---|---|---|---|---|---|---|---|
| vector_only | 0.583 | 0.723 | 0.793 | 0.860 | 0.583 | 0.647 | 0.663 | 0.672 |
| hybrid | 0.587 | 0.727 | 0.793 | 0.860 | 0.587 | 0.651 | 0.666 | 0.675 |
| hybrid_reranker | 0.680 | 0.803 | 0.843 | 0.843 | 0.680 | 0.739 | 0.748 | 0.748 |

## LLM Quality Evaluation

| Metric | Score |
|---|---|
| Avg Faithfulness    | 5.00 / 5.0 |
| Avg Answer Relevance | 5.00 / 5.0 |
| Samples evaluated   | 50 |

## Per-Sample LLM Judge Details

| # | Question | Faith. | Rel. | Reasoning |
|---|---|---|---|---|
| 1 | What is the recommended word count for a bio on enspiral.com?... | 5 | 5 | The answer accurately identifies the recommended word count provided in the source text. |
| 2 | What specific individual responsibilities are expected of employees re... | 5 | 5 | The answer accurately synthesizes the individual responsibilities and communication standards provid |
| 3 | If an employee decides to leave Blendle, what is the required notice p... | 5 | 5 | The answer accurately reflects the information provided in the context, correctly identifying the no |
| 4 | If a team is deciding whether to prioritize customer feedback in their... | 5 | 5 | The answer accurately synthesizes the provided context to offer a comprehensive and well-structured  |
| 5 | Why does the company believe that relying solely on posting job advert... | 5 | 5 | The answer accurately reflects the provided text, noting that while the company still uses job posti |
| 6 | If I am a new hire, how should I manage my time off given that unused ... | 5 | 5 | The answer correctly identifies that the policy depends on the specific company and provides accurat |
| 7 | What procedures must be followed by an employee planning a short remot... | 5 | 5 | The answer accurately distinguishes between the two company handbooks provided in the context and co |
| 8 | What is the name of the tool used to assess both technical skills and ... | 5 | 5 | The answer correctly identifies the Interview Scorecard as the tool mentioned in the provided contex |
| 9 | If an employee incurs a reimbursable business expense, what steps must... | 5 | 5 | The answer accurately synthesizes the specific reimbursement procedures provided in the context for  |
| 10 | What is the procedure for requesting or removing an Enspiral email acc... | 5 | 5 | The answer accurately summarizes the procedures for requesting and removing accounts as described in |
| 11 | What are the potential consequences for employees who behave in a way ... | 5 | 5 | The answer accurately synthesizes the disciplinary policies from the provided handbooks regarding su |
| 12 | What is the primary objective of the Clef drug and alcohol policy?... | 5 | 5 | The answer accurately identifies the primary objective and supporting details directly from the prov |
| 13 | If the 15th of the month falls on a Saturday, when should an employee ... | 5 | 5 | The answer accurately identifies the relevant policy from the Sparksuite handbook and correctly appl |
| 14 | Since what year has Blendle been a recognised sponsor by the IND?... | 5 | 5 | The answer directly addresses the question using the specific date provided in the retrieved context |
| 15 | How should a founder proceed if they receive a report about a colleagu... | 5 | 5 | The answer accurately synthesizes the provided handbooks to outline a comprehensive and professional |
| 16 | What are the specific financial administration responsibilities associ... | 5 | 5 | The answer accurately extracts the specific responsibilities listed in the provided context regardin |
| 17 | What does the company mean when they describe their managers as 'moonl... | 5 | 5 | The answer accurately defines the term based on the provided context and correctly distinguishes it  |
| 18 | If you are preparing to interview a candidate, how should you use the ... | 5 | 5 | The answer accurately synthesizes the provided context to explain how to use the interview outline,  |
| 19 | If you want to organize a company unconference in a new location, how ... | 5 | 5 | The answer accurately synthesizes the provided context to offer actionable advice on involving other |
| 20 | In what ways are staff members expected to contribute to the company's... | 5 | 5 | The answer accurately synthesizes the provided context to explain how staff contribute to brand buil |
| 21 | What is the status of Blendle regarding the IND, and what does this st... | 5 | 5 | The answer accurately identifies Blendle's status as a recognised sponsor and correctly explains the |
| 22 | Why does the organization encourage the practice of regularly reviewin... | 5 | 5 | The provided context does not contain any information regarding the practice of regularly reviewing  |
| 23 | What specific milestones and deliverables must a new employee complete... | 5 | 5 | The answer accurately synthesizes the provided context, correctly distinguishing between general onb |
| 24 | What is the required process for submitting a reimbursement request?... | 5 | 5 | The answer accurately synthesizes the different reimbursement processes provided in the context for  |
| 25 | What are the two primary purposes of the Proprietary Information and I... | 5 | 5 | The answer accurately identifies the two purposes of the PIIAA as stated in the provided context. |
| 26 | What is the company policy regarding travel expense reimbursements for... | 5 | 5 | The answer accurately distinguishes between the different company policies provided in the context a |
| 27 | What steps must be taken to successfully receive reimbursement for edu... | 5 | 5 | The answer accurately synthesizes the specific process for education reimbursement provided in the c |
| 28 | As a founder developing a new product, what four specific questions sh... | 5 | 5 | The answer accurately synthesizes the provided text to identify four key areas of inquiry for a foun |
| 29 | What definition does Seth Godin provide for the value of a brand?... | 5 | 5 | The answer accurately cites the two distinct definitions provided by Seth Godin within the retrieved |
| 30 | How should a founder ensure consistency in brand voice and tone across... | 5 | 5 | The answer accurately synthesizes the provided context to offer a comprehensive and well-structured  |
| 31 | What characterize the work responsibilities and scope of a Junior Desi... | 5 | 5 | The answer accurately summarizes the responsibilities and scope of a Junior Designer based solely on |
| 32 | What are the specific responsibilities of a Project Manager according ... | 5 | 5 | The model correctly identified that the provided context contains a header for the requested informa |
| 33 | If an employee wants to pursue a professional development course or pu... | 5 | 5 | The answer accurately synthesizes the provided context, correctly identifying that policies are comp |
| 34 | What are the specific hourly work requirements an employee must meet t... | 5 | 5 | The answer accurately extracts the specific hourly requirements for the Washington state voluntary p |
| 35 | What are the specific responsibilities included in the communications ... | 5 | 5 | The answer accurately synthesizes the communication responsibilities and standards found across the  |
| 36 | How should team members resolve a situation where more than one person... | 5 | 5 | The answer accurately synthesizes the provided context to explain the 'bun protocol' and the collabo |
| 37 | What specific behaviors are categorized as harassment under the commun... | 5 | 5 | The answer provides a comprehensive and accurate summary of the harassment behaviors described acros |
| 38 | Who is eligible to take new parent leave at Sparksuite?... | 5 | 5 | The answer accurately identifies that all full-time employees are eligible for new parent leave rega |
| 39 | How can companies utilize elements like notifications and micro-copy t... | 5 | 5 | The answer accurately synthesizes the provided context to explain how companies can use micro-copy a |
| 40 | What criteria must be met for an individual to join as a Member rather... | 5 | 5 | The provided context mentions that a guide on how to become a member exists in the handbook's struct |
| 41 | How often is the feedback cycle conducted, and what are the specific a... | 5 | 5 | The answer accurately distinguishes between the different companies mentioned in the context and pro |
| 42 | What is the required structure for documenting goals in the internal f... | 5 | 5 | The model correctly identifies that the specific term 'internal feedback tool' is absent from the co |
| 43 | If you are a Project Manager aiming to ensure the team is satisfied an... | 5 | 5 | The answer accurately synthesizes the provided handbooks to offer actionable advice on team satisfac |
| 44 | Which details are required regarding a venture's legal structure and b... | 5 | 5 | The answer accurately extracts the specific requirements for legal structure and business model from |
| 45 | If the shareholders decide that the current Board size is too small, w... | 5 | 5 | The answer correctly identifies that the provided context defines the board size but does not contai |
| 46 | If a contributor identifies an area for improvement within the documen... | 5 | 5 | The answer accurately synthesizes the provided documentation to explain the various methods and proc |
| 47 | If you are in the communications role, what steps should you take to e... | 5 | 5 | The answer synthesizes the provided handbooks into a coherent, actionable strategy that directly add |
| 48 | If a hiring manager is currently using only online job postings to fil... | 5 | 5 | The answer accurately synthesizes the company's proactive sourcing philosophy and operational guidel |
| 49 | At what time does the daily briefing for sharing learnings and optiona... | 5 | 5 | The answer correctly identifies the time mentioned in the context for the briefing involving learnin |
| 50 | What are the notification requirements for an employee working remotel... | 5 | 5 | The answer accurately synthesizes the varying requirements across the different company handbooks pr |
