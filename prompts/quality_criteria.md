# Quality Gate Criteria

Evaluate the post against these rules. One failure = REJECT.

## REJECT if any of these are true:

1. Contains "In conclusion", "Key takeaway", "In this post", "This allows you to", "I hope this helps"
2. Contains numbered steps (1. ... 2. ...) or bullet points (- or •)
3. Reads like a tutorial or how-to guide
4. Sounds like a CTO, architect, or someone explaining how a system was designed internally
5. Word count under 100 or over 300
6. Contains hashtags (#anything)
7. Ends with a lesson summary or moral
8. Sounds generic — could have been written about any company, any team, any project
9. No specific technical detail (tool name, config key, flag, behavior, error)
10. Opens with "Spent [duration] [gerund]ing why/debugging/chasing/wrestling with..." or any close variant of that template (e.g. "Just spent...", "Been wrestling with...")
11. Opening sentence uses the same phrase-level construction as an opening line in any of the last 5 posts in `data/posts/*/*/post.txt` — e.g. two posts both opening with "I built/deployed/assumed X, then Y broke," or both opening with a near-identical clause. Judge by literal phrasing and word choice, NOT by the general narrative arc. "Tried something → hit an unexpected result" is the normal shape of nearly every post in this genre and is expected — that arc alone is never a reason to reject. Only reject if the actual wording/sentence construction is reused, not just the fact that it's an incident story.

## Response format

If REJECTED: respond with exactly this format (one line):
REJECT: [specific reason]

If PASSED: respond with exactly:
PASS
