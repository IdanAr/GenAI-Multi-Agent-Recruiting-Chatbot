"""exit_fewshot.py - few-shot examples for the Exit Advisor (Phase 5).

Examples 1-7 are mined from the labeled data (sms_conversations.json,
conversations 1-5, the few-shot pool). They teach the subtle distinctions the
naive prompt got wrong:

- the candidate ACCEPTS a specific interview time  -> end (recruiter confirms)
- the candidate OPTS OUT / is not interested       -> end
- the candidate DECLINES one slot but stays engaged -> continue (offer another)
- the candidate is willing to schedule but not yet booked -> continue
- the candidate is asking about the role            -> continue
- the candidate accepts a time but asks a question  -> continue (mixed intent)

Examples 8-11 add different phrasing for patterns already covered above, since
the model had only ever seen one worked example of each and evaluation showed
that was not always enough signal.

Example 12 reinforces a pattern only example1 previously demonstrated, where a
real evaluation error recurred anyway: the candidate proposes their OWN
specific time, not one of the ones offered. That is still a commitment and
should end the conversation, not just accepting an offered slot.

No fine-tuning is used; these examples are injected into the prompt only.
"""

EXIT_FEWSHOT = """
# Examples

<example1>
Conversation:
Recruiter: No problem. How about Thursday at 4 PM instead?
Candidate: Monday at 3 PM is good.
Decision: {"decision": "end", "reason": "The candidate accepted a specific interview time, so the recruiter confirms and the conversation ends."}
</example1>

<example2>
Conversation:
Recruiter: Hybrid work model, with at least two days remote per week. Will you be able to meet next Wednesday at 10 AM?
Candidate: Wednesday at 10 AM works for me.
Decision: {"decision": "end", "reason": "The candidate confirmed the proposed time; nothing is left but to confirm and end."}
</example2>

<example3>
Conversation:
Recruiter: Our engineering manager can interview you Wednesday at 10 AM or Thursday at 2 PM. Which works best?
Candidate: Please remove me from your list. Thanks.
Decision: {"decision": "end", "reason": "The candidate opted out, so the conversation should end."}
</example3>

<example4>
Conversation:
Recruiter: Our engineering manager can interview you Wednesday at 10 AM or Thursday at 2 PM. Which works best?
Candidate: I can't at that time, I'm busy.
Decision: {"decision": "continue", "reason": "The candidate is unavailable for that slot but still engaged; offer another time."}
</example4>

<example5>
Conversation:
Recruiter: We currently deploy to AWS using Docker and ECS.
Candidate: Sounds great! I'd be happy to schedule a meeting.
Decision: {"decision": "continue", "reason": "The candidate is ready to schedule but no time is booked yet."}
</example5>

<example6>
Conversation:
Recruiter: How comfortable are you with SQL in addition to Python?
Candidate: Very comfortable. May I ask what technologies the current stack uses?
Decision: {"decision": "continue", "reason": "The candidate is asking about the role and remains engaged."}
</example6>

<example7>
Conversation:
Recruiter: I have openings on Tuesday at 1 PM or 3 PM. Do either work?
Candidate: Tuesday at 1 PM is perfect. Will this be a technical interview?
Decision: {"decision": "continue", "reason": "The candidate accepted a time but asked a new question, so the conversation must continue to provide the answer."}
</example7>

<example8>
Conversation:
Recruiter: Would you be available for a 30-minute interview on Thursday at 2pm or Friday at 10am?
Candidate: I can do Friday at 10am. That works well for me.
Decision: {"decision": "end", "reason": "The candidate accepted one of the offered times, so the recruiter confirms and the conversation ends."}
</example8>

<example9>
Conversation:
Recruiter: I wanted to see if you'd be open to discussing a Python Developer opportunity with us.
Candidate: Thanks for reaching out, but I actually just accepted another position and am no longer searching.
Decision: {"decision": "end", "reason": "The candidate has accepted another job and is no longer looking, so the conversation ends."}
</example9>

<example10>
Conversation:
Recruiter: Our main stack is Python with Django and FastAPI. Does that align with your experience?
Candidate: Yes, it does. What does a typical day look like for developers on your team?
Decision: {"decision": "continue", "reason": "The candidate is still asking questions about the role and remains engaged; no time has been discussed yet."}
</example10>

<example11>
Conversation:
Recruiter: Are you available for a quick call tomorrow at 11 AM to discuss our Python Developer opening?
Candidate: I already have a commitment at 11 AM tomorrow. Are there any other times that might work?
Decision: {"decision": "continue", "reason": "The candidate declined the offered time but is still interested and open to another slot."}
</example11>

<example12>
Conversation:
Recruiter: Would Tuesday at 11 AM or Thursday at 3 PM work for your interview?
Candidate: Actually, could we do Friday afternoon instead, say around 2 PM?
Decision: {"decision": "end", "reason": "The candidate proposed their own specific day and time. Even though it was not one of the options offered, it is still a concrete commitment, so the recruiter only needs to confirm and the conversation ends."}
</example12>
"""