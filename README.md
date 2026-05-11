# framebleed

local datamosh experiment.

framebleed is a local web app for cutting two clips together and generating a basic datamosh transition between them.

currently it can:

- upload two local video clips
- preview both clips in the browser
- choose start/end points for each clip
- generate a clean stitched mp4
- generate a datamoshed mp4
- preview/download the result
- validate clip time ranges before processing

## setup

requires python and ffmpeg.

on mac:

```bash
brew install ffmpeg
```

create and activate a venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

install python deps:

```bash
python3 -m pip install -r requirements.txt
```

## run

start the local backend:

```bash
uvicorn app.main:app --reload
```

then open:

```txt
http://127.0.0.1:8000
```

videos are processed locally on your machine.

## cli

the original cli still works.

clean export:

```bash
python3 mosh.py \
  --clip-a input/a.MOV \
  --clip-b input/b.MOV \
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
  --clip-a input/a.MOV \
  --clip-b input/b.MOV \
  --a-start 00:00:00 \
  --a-end 00:00:03 \
  --b-start 00:00:00 \
  --b-end 00:00:03 \
  --resolution 1080p \
  --output output/mosh_test.mp4 \
  --mosh
```

## project structure

```txt
app/
  main.py
  static/
    index.html

input/
output/
uploads/
working/

mosh.py
requirements.txt
```

## notes

test footage, uploads, generated outputs, and temporary working files are ignored by git.

this is still experimental. the next goal is to clean up the frontend files and improve the clip selection ui.
