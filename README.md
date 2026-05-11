# framebleed

local datamosh experiment.

right now this is just a python cli that:

- trims two clips
- joins them together
- exports a clean mp4
- removes the transition i-frame for a basic datamosh effect

## setup

requires python and ffmpeg.

on mac:

```bash
brew install ffmpeg
```

optional venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## usage

put two test clips in `input/`:

```txt
input/a.mov
input/b.mov
```

clean export:

```bash
python3 mosh.py \
  --clip-a input/a.mov \
  --clip-b input/b.mov \
  --a-start 00:00:00 \
  --a-end 00:00:03 \
  --b-start 00:00:00 \
  --b-end 00:00:03 \
  --resolution 1080p \
  --output output/clean_test.mp4
```

datamosh export:

```bash
python3 mosh.py \
  --clip-a input/a.mov \
  --clip-b input/b.mov \
  --a-start 00:00:00 \
  --a-end 00:00:03 \
  --b-start 00:00:00 \
  --b-end 00:00:03 \
  --resolution 1080p \
  --output output/mosh_test.mp4 \
  --mosh
```

## goal

eventually this should become a local web app where you can upload two clips, preview them, choose start/end points, generate a datamosh transition, and export the result.

## note

test footage and generated videos are ignored by git.
