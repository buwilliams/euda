# Chat

## Key Ideas

- **An Input, Not The Product**: chat is one way to tell Euda what's on your mind. It is deliberately not the first-class surface—[Focus](02-focus.md) is.
- **What's On Your Mind**: the chat prompt invites a person to offload a thought, which becomes memory, a topic, or an answer.
- **A Router To The Fleet**: in conversation, requests can be turned into work and routed to the right agent, rather than handled by one monolithic chatbot.
- **Feeds Learning**: every conversation is material for consolidation—chat is one of the richest sources Euda has for learning a person.

## Purpose

Chat exists so a person can speak to Euda naturally—to ask, to offload, to think out loud—without that becoming the entire relationship. Euda makes a deliberate choice here: it refuses to be a chatbot whose value is bounded by how much you type. Chat is an input into a system that mostly works in the background.

This matters because chat-first design quietly shifts the burden back onto the person: nothing happens unless you prompt it. Euda inverts that. The conversation is one channel; the curated Focus view and the background agents are where most of the value accrues.

## Expected Role

Chat should be a low-friction way in:

- accept what's on a person's mind and route it to the right outcome—an answer, a new topic, a memory;
- hand work to the appropriate agent rather than resolving everything in one thread;
- feed conversation into consolidation, so the system learns the person from how they actually talk;
- stay secondary to Focus, present on the same surface but not the center.

Current implementation details that matter to intent:

- In `v1`, chat is available alongside Focus, with a conversational agent that can create and manage other agents and route requests as topics.
- On `main`, chat is its own capability (`euda core chat`), consistent with the architecture where every capability is a distinct app.

Chat should not absorb the product. The moment everything must be typed into a conversation, Euda has lost its premise of managed attention and background work.

## Future Direction

As ambient surfaces arrive, "chat" naturally becomes voice—on wearables and smart devices—still as an input rather than the whole interface. The intent to preserve: a person can always just say what's on their mind, and Euda turns it into the right outcome, without conversation becoming the only way the system works for them.
