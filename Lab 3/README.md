# Chatterboxes

**Alexa Yang**

[![Watch the video](https://user-images.githubusercontent.com/1128669/135009222-111fe522-e6ba-46ad-b6dc-d1633d21129c.png)](https://youtu.be/LZ0VJClIlRI?si=Yy84mcyVYuVV19mn)

In this lab, we want you to design interaction with a speech-enabled device — something that listens and talks to you. This device can do anything _but_ control lights (since we already did that in Lab 1). First, we want you to storyboard what you imagine the conversational interaction to be like. Then you will use wizarding techniques to elicit examples of what people might say, ask, or respond. We then want you to use the examples collected from at least two other people to inform the redesign of the device.

We will focus on **audio** as the main modality for interaction to start; these general techniques can be extended to **video**, **haptics** or other interactive mechanisms in the second part of the Lab.

A note on what you are building with. Speech interfaces are usually taught as two boxes — speech-in, speech-out — and that framing hides the part that actually determines whether an interaction works. Between listening and speaking sits the question of **whose turn it is**: when does the device decide you have finished talking, and how long does it make you wait before it answers? This lab gives you direct control over both, and we will ask you to notice what changes when you move them.

## Prep for Part 1: Get the Latest Content and Pick up Additional Parts

Please check instructions in [prep.md](prep.md) and complete the setup.

### Pick up Web Camera If You Don't Have One

Students who have not already received a web camera will receive their Webcam and at the beginning of lab. If you cannot make it to class this week, please contact the TAs to ensure you get these.

### Get the Latest Content

As always, pull updates from the class Interactive-Lab-Hub to both your Pi and your own GitHub repo.

**\[recommended\]** Option 1: On the Pi, `cd` to your `Interactive-Lab-Hub`, pull the updates from upstream (class lab-hub) and push the updates back to your own GitHub repo. You will need the _personal access token_ for this.

```
pi@ixe00:~$ cd Interactive-Lab-Hub
pi@ixe00:~/Interactive-Lab-Hub $ git pull upstream Fall2026
pi@ixe00:~/Interactive-Lab-Hub $ git add .
pi@ixe00:~/Interactive-Lab-Hub $ git commit -m "get lab3 updates"
pi@ixe00:~/Interactive-Lab-Hub $ git push
```

Option 2: On your own GitHub repo, create a pull request to get updates from the class Interactive-Lab-Hub. After you have the latest updates online, go to your Pi, `cd` to your `Interactive-Lab-Hub` and use `git pull`.

---

# Part 1

## Setup

Create and activate a virtual environment for this lab:

```
pi@ixe00:~$ cd Interactive-Lab-Hub/Lab\ 3
pi@ixe00:~/Interactive-Lab-Hub/Lab 3 $ python3 -m venv .venv
pi@ixe00:~/Interactive-Lab-Hub/Lab 3 $ source .venv/bin/activate
(.venv) pi@ixe00:~/Interactive-Lab-Hub/Lab 3 $
```

Install the Python dependencies:

```
(.venv) $ pip install -r requirements.txt
```

This takes a few minutes. If you would like it to take considerably less time, [`uv`](https://docs.astral.sh/uv/) is a drop-in replacement for `pip` that is dramatically faster on the Pi:

```
(.venv) $ pip install uv && uv pip install -r requirements.txt
```

Then run the setup script, which installs the classic speech synthesizers, downloads the voice activity detection model, and pre-fetches a neural voice and a speech recognition model so you are not waiting on downloads during lab:

```
(.venv):~$ cd speech-scripts
(.venv) $ ./setup.sh
```

Check your audio devices before going further. `arecord -l` lists capture devices and `aplay -l` lists playback devices; if your webcam microphone or Bluetooth speaker does not appear, fix that first — every script below assumes the system defaults are the ones you want.

## A. Text to Speech

Your Pi can speak in several quite different ways, and the differences are audible in a way that matters for design. In `speech-scripts/` there are shell scripts for each.

### The classic engines

```
(.venv) $ cd speech-scripts

(.venv) $ sudo apt update
(.venv) $ sudo apt install -y espeak festival festvox-kallpc16k

(.venv) $ ./espeak_demo.sh
(.venv) $ ./festival_demo.sh
```

You can run these `.sh` files by typing `./filename`, and read one with `cat filename`. You can also play audio files directly with `aplay filename` — try `aplay lookdave.wav`.

These are all decades-old technology and they sound like it. `espeak-ng` is a _formant synthesizer_: it generates speech from an acoustic model of the vocal tract, which is why it sounds robotic but also why the whole thing fits in a couple of megabytes and responds instantly. `festival` is _concatenative_: they stitch together recorded fragments of a real speaker, which sounds more human but breaks audibly at the seams.

### Neural TTS with Piper

Note that the Piper command line changed in version 1.x — voices are now downloaded explicitly with `python3 -m piper.download_voices`, and you invoke it as `python3 -m piper`. Tutorials you find online may show the old `echo ... | piper --model ...` form, which no longer works. Browse the [voice samples](https://rhasspy.github.io/piper-samples) and download a different one if you'd like:

```
(.venv) $ python3 -m piper.download_voices en_US-lessac-medium
```

[Piper](https://github.com/OHF-Voice/piper1-gpl) synthesizes speech with a small neural network, runs comfortably on the Pi 5, and sounds markedly better than the above.

```
(.venv) $ ./piper_demo.sh
```

The demo script also shows `--output-raw`, which streams audio to the speaker as it is generated rather than writing a file first. Listen for the difference in how quickly speech begins. In a conversational system this gap is the thing your user experiences as responsiveness.

\*\***Write your own shell file to use your favorite of these TTS engines to have your Pi greet you by name.**\*\*
(This shell file should be saved to your own repo for this lab.)

alexagreeting.sh

\*\***Then answer: Is the same greeting, in these different voices, the same greeting? Describe one concrete way the voice changed what the utterance seemed to mean or who seemed to be speaking.**\*\*

Deeper voices almost come off as more "hostile" and serious. Piper's voice seemed the most neutral to positive, which is why I used her for my alexagreeting.sh. The faster Piper spoke, the more energetic and engaged she seemed; however, the slower speech felt more natural.

## B. Speech to Text

We use [faster-whisper](https://github.com/SYSTRAN/faster-whisper), a reimplementation of OpenAI's Whisper model that runs several times faster on CPU and does not require PyTorch. All processing happens on the Pi; nothing is sent to a server.

```
(.venv) $ python transcribe.py lookdave.wav
```

The transcript is not the interesting output here — the timings are. Run it again with a larger model and compare:

```
(.venv) $ python transcribe.py lookdave.wav --model base.en
(.venv) $ python transcribe.py lookdave.wav --model small.en
#  noted that the first run may take longer because the model is downloaded, and that the HF unauthenticated-request warning is expected and not an error.
```

Available sizes, smallest first: `tiny.en`, `base.en`, `small.en`, `medium.en`. The `.en` variants are English-only and faster than their multilingual counterparts at the same size.

BASE:
model base.en (int8, beam=1)
audio duration 3.72s
model load 2.66s
transcription 2.23s
real-time factor 0.60x

SMALL:
model small.en (int8, beam=1)
audio duration 3.72s
model load 6.44s
transcription 5.91s
real-time factor 1.59x

\*\***Record a few seconds of your own speech (`arecord -d 5 -f cd -c 1 -r 16000 test.wav`) and transcribe it with at least two model sizes. Report the real-time factor for each. At what point does the accuracy improvement stop being worth the delay, for a system that has to answer you?**\*\*

TINY:Hello dear, how are you today?

model tiny.en (int8, beam=1)
audio duration 5.00s
model load 0.52s
transcription 1.00s
real-time factor 0.20x

BASE: Hello dear, how are you today?

model base.en (int8, beam=1)
audio duration 5.00s
model load 0.69s
transcription 1.91s
real-time factor 0.38x

SMALL: Hello dear, how are you today?

model small.en (int8, beam=1)
audio duration 5.00s
model load 1.21s
transcription 5.44s
real-time factor 1.09x

I think the time delay is worth it only if iterating and improving can be recognized by the algorithm easily. There should be a way to shortcut to the problem area, improve, and test in a constrained sort of way without having to rerun the entire program and wait for it to complete only to see that your updates haven't properly fixed the issue. It also is in proportion to the task. I only had a short, simple phrase to transcribe here, but if I had a much longer phrase then it would make sense it takes longer.

\*\***Write your own script that verbally asks for a numerical input (a phone number, zipcode, number of pets) and records the answer the respondent provides.**\*\* Numbers are a good stress test — transcription systems make characteristic errors on digit strings, and you will want to know what they are before you design around them.

sugar_question.sh

Transcribing...

2, 2 and 20.

model tiny.en (int8, beam=1)
audio duration 5.00s
model load 0.54s
transcription 0.89s
real-time factor 0.18x

## C. Turn-taking: knowing when someone has stopped talking

Everything so far has worked on fixed audio files. A real conversational device does not get told when to start and stop recording — it has to decide. This is the problem that makes speech interfaces hard, and it is mostly not a speech recognition problem.

We use a **voice activity detector** (VAD) to segment the microphone stream into utterances. `listen.py` runs Silero VAD continuously and hands each detected utterance to faster-whisper:

```
(.venv) $ cd speech-scripts
(.venv) $ python listen.py
```

Speak, pause, and watch it transcribe. Now change the endpointing threshold — the amount of silence the system requires before it decides your turn is over:

```
(.venv) $ python listen.py --min-silence 0.2
(.venv) $ python listen.py --min-silence 1.5
```

\*\***Try both extremes, and something in between. Describe what each one feels like to talk to. Note specifically: at 0.2s, what kinds of normal speech get cut off? At 1.5s, what does the delay make the system seem like?**\*\*

[0.6s speech, 3.90s to transcribe] Story time.
[9.3s speech, 1.76s to transcribe] At half past six, on the 21st of June 1922, when Cup Alexander Iliczrostov was escorted through the gates of the Kremlin onto spread square.
[1.1s speech, 0.78s to transcribe] It was glorious.
[0.4s speech, 0.78s to transcribe] Cool.
[2.7s speech, 0.92s to transcribe] Drawing his shoulders back without breaking stride.
[2.8s speech, 1.05s to transcribe] They count inhale the air like one fresh from a swim.
[4.5s speech, 1.10s to transcribe] The sky was the very blue that the couple of those sand vessels had been painted for.
[4.3s speech, 1.19s to transcribe] their pink screens and gold shimmered as if they were the sole purpose of a religion.
[1.5s speech, 0.90s to transcribe] to cheer its divinity.

[20.9s speech, 2.86s to transcribe] A half past six on the 21st of June 1922, when Count Alexander Iliage Roestov was escorted through the gates of the Kremlin on Tresquare if was glorious and cool. Drawing his shoulders back without breaking stride, the count inhaled the air like one fresh from a swim. The sky was the very blue that the couple of those of St. Basil had been painted for.

I feel as though the shorter transcription time might be better for conversations, which are generally more fast paced and contain a lot more filler words such as "like, um, er" etc. The short recording time would likely cut many of these out. Whereas the longer recording time could be better for presentations, speeches, and orations, where the words are more prepared and there is more content to be captured in every second.

There is no correct value. A system that takes drink orders and a system that listens to someone think out loud want very different thresholds, and the right one depends on what your users are doing with their pauses.

### The complete loop

`echo_bot.py` puts the pieces together: it listens, endpoints, transcribes, and speaks a reply through Piper. The dialogue policy is deliberately trivial — it repeats what you said — so that everything you notice is a property of the timing rather than the content.

```
(.venv) $ python echo_bot.py
```

## D. Storyboard

Storyboard and/or use a Verplank diagram to design a speech-enabled device. (Stuck? Make a device that talks for dogs. If that is too stupid, find an application that is better than that.)

\*\***Post your storyboard and diagram here.**\*\*

Write out what you imagine the dialogue to be. Use cards, post-its, or whatever method helps you develop alternatives or group responses.

\*\***Please describe and document your process.**\*\*

Your script should include the pauses. Where does your device wait, and for how long? You now know from Part C that this is a parameter you have to choose, not something that happens for free.

## E. Acting out the dialogue

Find a partner, and _without sharing the script with your partner_ try out the dialogue you've designed, where you (as the device designer) act as the device you are designing. Please record this interaction (for example, using Zoom's record feature).

Recording: https://drive.google.com/file/d/1lvE-jcHej_ZCVtguHhQdMHiL-gTKWCbv/view?usp=sharing

\*\***Describe if the dialogue seemed different than what you imagined when it was acted out, and how.**\*\*

I elected not to include the opening dialogue I wrote out in the original planning stage (the, "welcome to the pocket poshificator!" part) to see if the purpose of the device was intuitive. It didn't take long for my user to pick up on it, which signals that the device clearly fulfills its objective. It honestly mostly played out how I imagined it, although I will have to work on the script because there are only so many ways you can make a phrase posh. I also need to figure out if the device ought to vocally mimic the attitude of the user; right now, I'm using kind of a neutral tone for all the responses, but expressing emotion is a part of being posh and should therefore be reflected accordingly.

---

# Lab 3 Part 2

For Part 2, you will redesign the interaction with the speech-enabled device using the data collected, as well as feedback from part 1.

## Prep for Part 2

1. What are concrete things that could use improvement in the design of your device? For example: wording, timing, anticipation of misunderstandings.
2. What are other modes of interaction _beyond speech_ that you might also use to clarify how to interact? In particular: how does someone know when the device is listening, and when it is thinking? You have a screen and an LED.
3. Make a new storyboard, diagram and/or script based on these reflections.
4. (optional) Integrate [input devices](inputs.md) in the system

## Prototype your system

The system should:

- use the Raspberry Pi
- use one or more sensors
- require participants to speak to it

_Document how the system works._

_Include videos or screencaptures of both the system and the controller._

## Test the system

Try to get at least two people to interact with your system. (Ideally, you would inform them that there is a wizard _after_ the interaction, but we recognize that can be hard.)

Answer the following:

### What worked well about the system and what didn't?

\*\*_your answer here_\*\*

### What worked well about the controller and what didn't?

\*\*_your answer here_\*\*

### What lessons can you take away from the WoZ interactions for designing a more autonomous version of the system?

\*\*_your answer here_\*\*

### How could you use your system to create a dataset of interaction? What other sensing modalities would make sense to capture?

\*\*_your answer here_\*\*

<details>
  <summary><strong>Submission Cleanup Reminder (Click to Expand)</strong></summary>

**Before submitting your README.md:**

- This readme.md file has a lot of extra text for guidance.
- Remove all instructional text and example prompts from this file.
- You may either delete these sections or use the toggle/hide feature in VS Code to collapse them for a cleaner look.
- Your final submission should be neat, focused on your own work, and easy to read for grading.
</details>
