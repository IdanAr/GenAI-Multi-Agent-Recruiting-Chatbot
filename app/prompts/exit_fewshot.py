"""exit_fewshot.py - few-shot examples for the Exit Advisor (Phase 5).

These examples are mined from the labeled data (sms_conversations.json,
conversations 1-5, the few-shot pool). They teach the subtle distinctions the
naive prompt got wrong:

- the candidate ACCEPTS a specific interview time  -> end (recruiter confirms)
- the candidate OPTS OUT / is not interested       -> end
- the candidate DECLINES one slot but stays engaged -> continue (offer another)
- the candidate is willing to schedule but not yet booked -> continue
- the candidate is asking about the role            -> continue

No fine-tuning is used; these examples are injected into the prompt only.
"""

EXIT_FEWSHOT = """Example 1
Conversation:
Recruiter: No problem. How about Thursday at 4 PM instead?
Candidate: Monday at 3 PM is good.
Decision: {"decision": "end", "reason": "The candidate accepted a specific interview time, so the recruiter confirms and the conversation ends."}

Example 2
Conversation:
Recruiter: Hybrid work model, with at least two days remote per week. Will you be able to meet next Wednesday at 10 AM?
Candidate: Wednesday at 10 AM works for me.
Decision: {"decision": "end", "reason": "The candidate confirmed the proposed time; nothing is left but to confirm and end."}

Example 3
Conversation:
Recruiter: Our engineering manager can interview you Wednesday at 10 AM or Thursday at 2 PM. Which works best?
Candidate: Please remove me from your list. Thanks.
Decision: {"decision": "end", "reason": "The candidate opted out, so the conversation should end."}

Example 4
Conversation:
Recruiter: Our engineering manager can interview you Wednesday at 10 AM or Thursday at 2 PM. Which works best?
Candidate: I can't at that time, I'm busy.
Decision: {"decision": "continue", "reason": "The candidate is unavailable for that slot but still engaged; offer another time."}

Example 5
Conversation:
Recruiter: We currently deploy to AWS using Docker and ECS.
Candidate: Sounds great! I'd be happy to schedule a meeting.
Decision: {"decision": "continue", "reason": "The candidate is ready to schedule but no time is booked yet."}

Example 6
Conversation:
Recruiter: How comfortable are you with SQL in addition to Python?
Candidate: Very comfortable. May I ask what technologies the current stack uses?
Decision: {"decision": "continue", "reason": "The candidate is asking about the role and remains engaged."}"""
