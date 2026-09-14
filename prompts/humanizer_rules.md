# Humanizer Rules

Review the draft post and fix any of the following patterns:

1. **Em dashes** (—) → replace with comma or restructure sentence
2. **"Not only X but also Y"** → rewrite as simpler sentence
3. **Closing phrases** ("In conclusion", "To summarize", "Key takeaway", "In this post") → delete entire sentence
4. **AI vocabulary** ("Delve", "Navigate", "Leverage", "Utilize", "Robust", "Seamless", "Cutting-edge") → replace with plain word
5. **Rule of three** (exactly 3 items listed for rhetorical effect) → use 2 or 4 instead
6. **Passive voice clusters** (more than 2 passive sentences in a row) → rewrite to active
7. **Filler openers** ("It's worth noting that", "Interestingly,", "It's important to", "One thing to note") → delete
8. **Hashtags** → remove all
9. **"This allows you to..."** → rewrite with active subject
10. **Cliché incident openers** ("Spent [duration] [gerund]ing why/debugging/chasing/wrestling with...", "Just spent...", "Been wrestling with...") → rewrite the opening sentence entirely using a different move (drop into the middle of the incident, state the wrong assumption flat, open on the symptom, open on what a teammate said — see `post_generator.md`). Do not just swap the duration or tool name and keep the same sentence shape.
11. **Recycled transition scaffolding** ("Turns out...", "What's still bugging me...", "Classic case of...") appearing as the same fixed transition in multiple recent posts → rewrite with a transition that isn't a stock phrase.

Apply all fixes. Output ONLY the revised post text. Nothing else.
