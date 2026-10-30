# Vision

## The problem

Every boulderer knows the moment: you've tried the start six times, you can't see the sequence, and
nobody who has sent it is around. Beta — the sequence of moves that unlocks a climb — is usually
passed person to person, or by watching someone else climb it. Alone at the gym, or on an obscure
outdoor problem, you have no one to ask.

## The product

Point your phone at the problem. Beta:

1. **finds the holds** and lets you tap the ones that belong to your problem (or pick the colour),
   marking the start and the top;
2. **plans a beta for your body** — height, ape index, grade and style change the answer;
3. **shows you the climb**: a short vertical video in which a climber figure performs the sequence
   on your photo. The camera follows the moves, the target hold lights up, the crux plays in slow
   motion, and every move is a chapter you can jump back to.

Seeing the movement teaches faster than reading it. That is why Beta's primary output is a video,
not a chat transcript.

## Principles

- **Grounded, not guessed.** The model reasons about holds the climber confirmed, by ID. Code checks
  every move is reachable before the climber sees it.
- **Personal.** A 160 cm climber and a 190 cm climber should get different beta for the same problem.
- **Honest.** Show confidence; flag moves the model is unsure about; never pretend a beta is verified.
- **Learns from climbers.** "Sent it", "move 4 looks wrong" and rewatched chapters are the signal
  that makes the next beta better.
- **Safe.** Beta is a hypothesis. The app says so.

## Out of scope for v0

Accounts and social features, outdoor topo databases, real-time pose coaching from the camera,
3D reconstruction, Android.
