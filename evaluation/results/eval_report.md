# Evaluation Report

**Generated:** 2026-08-04 05:57:20  
**Ground Truth Size:** 300 Q&A pairs

## Retrieval Evaluation

| Strategy | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@1 | MRR@3 | MRR@5 | MRR@10 |
|---|---|---|---|---|---|---|---|---|
| vector_only | 0.127 | 0.170 | 0.180 | 0.190 | 0.127 | 0.147 | 0.149 | 0.151 |
| hybrid | 0.137 | 0.190 | 0.200 | 0.210 | 0.137 | 0.161 | 0.163 | 0.165 |
| hybrid_reranker | 0.197 | 0.210 | 0.213 | 0.213 | 0.197 | 0.203 | 0.204 | 0.204 |

## LLM Quality Evaluation

| Metric | Score |
|---|---|
| Avg Faithfulness    | 5.00 / 5.0 |
| Avg Answer Relevance | 5.00 / 5.0 |
| Samples evaluated   | 30 |

## Per-Sample LLM Judge Details

| # | Question | Faith. | Rel. | Reasoning |
|---|---|---|---|---|
| 1 | What specific information must be included when filling out the airtab... | 5 | 5 | The provided context does not contain any information regarding an Airtable profile form, so the mod |
| 2 | What are the specific individual responsibilities for employees regard... | 5 | 5 | The answer accurately extracts the specific responsibilities listed in the provided context for indi |
| 3 | How should a current Blendle employee sign up for a membership at dewo... | 5 | 5 | The answer accurately reflects the instructions provided in the context for signing up for the disco |
| 4 | If a customer provides feedback on a product, how should the business ... | 5 | 5 | The provided context does not contain information regarding how a business should respond to custome |
| 5 | What are the specific requirements and ethical guidelines for handling... | 5 | 5 | The answer accurately extracts the specific ethical and operational guidelines for sourcing candidat |
| 6 | If I am available for 40 hours per week, how can I be certain that the... | 5 | 5 | The provided context does not contain information regarding task assignment or workload guarantees,  |
| 7 | What notification and coordination steps must an employee take when pl... | 5 | 5 | The answer accurately extracts the required notification steps from the provided context and correct |
| 8 | What is the name of the tool used to assess both technical skills and ... | 5 | 5 | The provided context does not contain information about a tool used to assess technical skills and c |
| 9 | How should an employee report their mileage at the end of the month to... | 5 | 5 | The provided context contains a section on travel but lacks any specific instructions regarding mile |
| 10 | What is the primary benefit of using a group for email addresses at En... | 5 | 5 | The model correctly identified that the provided context does not contain information regarding the  |
| 11 | What are the potential consequences for employees who do not adhere to... | 5 | 5 | The provided context does not contain information regarding drug and alcohol consumption policies, s |
| 12 | What is the primary objective of the company's drug and alcohol policy... | 5 | 5 | The provided context does not contain information regarding a drug and alcohol policy, so the model  |
| 13 | If a scheduled payday falls on a Saturday, when should an employee exp... | 5 | 5 | The provided context does not contain information regarding direct deposit schedules for employees,  |
| 14 | How long can the migration and relocation procedure take for new hires... | 5 | 5 | The provided context does not contain information regarding migration or relocation procedures for n |
| 15 | How should a founder proceed if they receive a report regarding harass... | 5 | 5 | The model correctly identified that the provided context does not contain information regarding the  |
| 16 | What are the specific financial administration responsibilities regard... | 5 | 5 | The provided context does not contain any information regarding Xero or specific financial administr |
| 17 | What tasks are expected of team members in terms of their daily contri... | 5 | 5 | The answer accurately extracts the available information for the Junior Customer Support role and co |
| 18 | If you are conducting an interview and want to minimize personal bias,... | 5 | 5 | The answer accurately synthesizes the provided handbooks to offer concrete, actionable steps for min |
| 19 | If a company is considering moving its office to a new location, how s... | 5 | 5 | The provided context does not contain information regarding office relocation or office supplies, so |
| 20 | In what ways are employees expected to represent the company to the pu... | 5 | 5 | The provided context does not contain information regarding how employees are expected to represent  |
| 21 | What is the required process for a lead to follow when extending a job... | 5 | 5 | The answer accurately extracts the hiring process steps from the provided context while correctly id |
| 22 | How does the organization ensure that its documentation remains curren... | 5 | 5 | The provided context does not contain information regarding how the organization maintains or update |
| 23 | What objectives must be met during the first month to demonstrate prog... | 5 | 5 | The provided context does not contain information regarding first-month objectives, and the model co |
| 24 | What is the required procedure for submitting a reimbursement request?... | 5 | 5 | The answer accurately synthesizes the reimbursement procedures for Blendle from the provided context |
| 25 | What are the two primary purposes of the Proprietary Information and I... | 5 | 5 | The provided context does not contain information regarding the Proprietary Information and Inventio |
| 26 | What is the company's policy regarding pension contributions and which... | 5 | 5 | The answer accurately identifies the pension provider and policy details based on the provided conte |
| 27 | How much funding does each staff member receive per year for professio... | 5 | 5 | The answer accurately extracts the varying policies for each company mentioned in the provided conte |
| 28 | When evaluating whether a new product can function as a stand-alone br... | 5 | 5 | The answer accurately identifies the four specific questions provided in the source text for evaluat |
| 29 | What definition does Seth Godin provide for a brand's total value?... | 5 | 5 | The answer accurately quotes the definition provided by Seth Godin found in the retrieved context. |
| 30 | How should a founder ensure that brand voice and tone are effectively ... | 5 | 5 | The answer is highly accurate, well-structured, and directly addresses the prompt using the provided |
