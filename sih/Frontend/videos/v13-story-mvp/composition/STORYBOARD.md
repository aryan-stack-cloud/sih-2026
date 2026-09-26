# v11 storyboard: "How do you catch a signal that lasts a split second?"

Infographics-Show style cartoon story. Design truth: `design.md`. Narration: `narration.txt`.
Timing is driven by the real voice clip durations (`assets/voice/durations.json`) through
`plan.json`; scene code uses cue names (`K.cue("s01_2")`) instead of hard-coded seconds.

## Frame 1
status: outline
src: scenes/s01.html
rules: viewport-change, spring-pop-entrance, particle-burst, sine-wave-loop
Night. The 16-room building, the guard in his booth, searchlight on rooms 1-2. A torch flashes in
room 11 and dies before the beam arrives; red "MISSED!" stamp; guard bubble "Not AGAIN!". Tag:
"THE PROBLEM: signals last a split second".

## Frame 2
status: outline
src: scenes/s02.html
rules: spring-pop-entrance, svg-path-draw, stat-bars-and-fills, kinetic-beat-slam
Guard's thought cloud: a giant searchlight. Engineer: "Not in real hardware!" Cut to the real
receiver chain (antenna -> receiver -> laptop); the beam is a narrow slice of a wide spectrum bar,
arrow label "INSTANTANEOUS BANDWIDTH", ">=10x narrower" (problem statement). Rooms fold into 16
bands, window covers 2 (simulator). Statement card: "WE CAN'T MAKE THE LIGHT BIGGER. WE CAN MAKE
IT SMARTER."

## Frame 3
status: outline
src: scenes/s03.html
rules: svg-icon-enrichment, counting-dynamic-scale, spring-pop-entrance
Clock-hand sweep over the 16 bands. An intruder with a metronome flashes just after the beam
leaves, every time. Counter "CAUGHT: 0" stamps. Tag "TEST: rhythm trap".

## Frame 4
status: outline
src: scenes/s04.html
rules: svg-path-draw, waterfall-entry, spring-pop-entrance
Engineer at a whiteboard draws the loop LOOK -> LEARN -> PICK -> MOVE ("every 10 ms"). Three
family doors: FOLLOW RULES / LEARN FROM EXPERIENCE / NEURAL NETWORKS with 2 icons each.

## Frame 5 to Frame 10 (the six methods)
status: outline
src: scenes/s05.html ... scenes/s10.html
rules: kinetic-beat-slam (giant #N card), spring-pop-entrance, svg-icon-enrichment, viewport-change
Each opens on a giant "#N" card over the blurred scene, then the household object acts out the
method, with the 2-of-16 window reacting on a band strip, and a name plate + family chip:
#1 CTMC dice, #2 Index to-do list + alarm clock, #3 Bandit slot machines + coins,
#4 Q-learning cheat sheet, #5 DQN robot brain, #6 PPO prize wheel.

## Frame 11
status: outline
src: scenes/s11.html
rules: spring-pop-entrance, stat-bars-and-fills, counting-dynamic-scale
Case file "TRAINING DATA" with two photos (simulator worlds; Alan Turing Institute synthetic
radar dataset). Exam desk "never-seen runs". Stopwatch race of measured training times.

## Frame 12
status: outline
src: scenes/s12.html
rules: counting-dynamic-scale, stat-bars-and-fills, particle-burst, spring-pop-entrance
Control-room big screen: rhythm trap result (sweep 0, dice and to-do list found it every time),
100-square grids 11 vs 13 (+22%), 97% reach, Bandit 34/100 but 71% reach, 6.6 ms decision.

## Frame 13
status: outline
src: scenes/s13.html
rules: ambient-glow-bloom, spring-pop-entrance, sine-wave-loop
Sunrise over the building, guard with chai, final statement card and PUSHPAK logo.
