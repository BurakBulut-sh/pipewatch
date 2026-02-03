# 🔬 Pipewatch - Explained Simply

> **TL;DR**: Pipewatch is like a fitness tracker for your bioinformatics jobs. It watches what your computer is doing and tells you what happened afterwards.

---

## What Problem Does This Solve? 🤔

Imagine you're baking 100 cakes (running 100 DNA samples). You're really busy, and things keep going wrong:

- Some cakes burn (jobs fail)
- Some take forever (slow steps)
- You run out of ingredients (not enough memory)
- You forget which recipe you used (no record of what happened)

**Pipewatch** is like having a kitchen assistant that:
- Writes down when you started and finished each cake
- Notes how hot the oven was (resource usage)
- Tells you which step took the longest
- Points out which cakes failed and why

---

## The Two Main Parts 🏗️

### Part 1: `obsrun` - The Camera 📹

Think of `obsrun` like a security camera that watches your computer while it works.

When you run a command like:
```bash
obsrun "bwa mem reference.fa reads.fq > output.bam"
```

It does THREE things:
1. **Before**: Writes down "I'm starting this job at 2:00 PM"
2. **During**: Runs your command normally (bwa does its thing)
3. **After**: Writes down "Job finished at 2:05 PM, took 5 minutes, used 4GB memory, exit code 0"

All this info gets saved to a file called `pipewatch-events.ndjson` (think of it as a diary).

### Part 2: `pipewatch report` - The Storyteller 📊

Now you have this diary full of facts. But reading raw facts is boring! 

`pipewatch report` reads the diary and makes pretty charts:
- "Your slowest step was 'alignment' - it took 60% of your time"
- "Sample #42 kept failing - maybe check that file"
- "You requested 8GB memory but only used 4GB - you can ask for less next time"

---

## How Does It Actually Work? 🔧

### The Simple Version

```bash
# 1. Wrap your command with obsrun
obsrun "your_command_here"

# 2. Look at what happened
cat pipewatch-events.ndjson
```

### The Real-World Version (Slurm Cluster)

You have a script `run.sh` that looks like this:
```bash
#!/bin/bash
#SBATCH --array=1-100  # Run 100 jobs

# Get sample name from list
SAMPLE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" samples.txt)

# Align DNA
srun bwa mem reference.fa ${SAMPLE}_1.fq ${SAMPLE}_2.fq > ${SAMPLE}.bam

# Sort the result  
srun samtools sort ${SAMPLE}.bam -o ${SAMPLE}.sorted.bam
```

**With Pipewatch, you change it to:**
```bash
#!/bin/bash
#SBATCH --array=1-100

SAMPLE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" samples.txt)

# Wrap each step with obsrun
obsrun "bwa mem reference.fa ${SAMPLE}_1.fq ${SAMPLE}_2.fq > ${SAMPLE}.bam"
obsrun "samtools sort ${SAMPLE}.bam -o ${SAMPLE}.sorted.bam"
```

Now each step gets recorded! 📋

---

## What Information Gets Saved? 📝

For every command, Pipewatch records:

| Thing | Example | Why It Matters |
|-------|---------|----------------|
| **When** | 2024-01-15 14:30:22 | Know exactly when things happened |
| **Hostname** | node42.cluster | Which computer did the work |
| **Command** | `bwa mem ref.fa reads.fq` | What exactly was run |
| **Step Name** | "alignment" | Group similar tasks together |
| **Sample ID** | "patient_001" | Track per-sample stats |
| **SLURM Job** | 12345 | Link to cluster scheduler |
| **Exit Code** | 0 (success) or 1 (failed) | Did it work? |
| **Duration** | 45,000 ms (45 seconds) | How long did it take |
| **Memory** | 4,194,304 KB (4 GB) | Did you use too much/too little? |
| **Git Commit** | abc123def | What version of code was used |

---

## Real Example Walkthrough 🚶

### Step 1: Run Something
```bash
$ obsrun "sleep 2 && echo hello"
hello
```

### Step 2: Check What Was Recorded
```bash
$ cat pipewatch-events.ndjson
```

Output:
```json
{"event_type":"start","timestamp":"2024-01-15T14:30:00","command":"sleep 2 && echo hello"}
{"event_type":"end","timestamp":"2024-01-15T14:30:02","command":"sleep 2 && echo hello","exit_code":0,"duration_ms":2005}
```

Translation:
- ✅ The command started
- ✅ It finished 2 seconds later
- ✅ Exit code 0 means success
- ✅ It took 2005 milliseconds

### Step 3: Make a Pretty Report
```bash
$ pipewatch report pipewatch-events.ndjson -o my_report/
```

Now open `my_report/index.html` in your browser and see pretty charts! 📊

---

## Common Use Cases 🎯

### "Why is my pipeline so slow?"
```bash
# Run your steps with obsrun
obsrun "step1"
obsrun "step2" 
obsrun "step3"

# Generate report
pipewatch report pipewatch-events.ndjson -o report/
# Look at "Top Slowest Steps" section
```

### "Which samples keep failing?"
```bash
# After running your array job
pipewatch report events/*.ndjson -o report/
# Look at "Failure Clustering" section
```

### "Did my code change make things slower?"
```bash
# Run with old code, save events
mv pipewatch-events.ndjson baseline.ndjson

# Run with new code
./run_new_version.sh

# Compare!
pipewatch report pipewatch-events.ndjson --compare-with baseline.ndjson -o comparison/
```

---

## The Magic Behind the Scenes ✨

### How does obsrun measure time?

It uses the `date` command before and after your command:
```bash
# Start time
start=$(date +%s%3N)  # milliseconds since 1970

# Your command runs here
sleep 2

# End time
end=$(date +%s%3N)

# Calculate difference
duration=$((end - start))  # = 2000 milliseconds
```

### How does it measure memory?

On Linux with GNU time, it runs:
```bash
/usr/bin/time -v your_command
```

This outputs something like:
```
Maximum resident set size (kbytes): 4194304
```

Which means "your program used 4GB of RAM at peak"

### Why NDJSON format?

NDJSON = "Newline Delimited JSON"

Instead of one big JSON file:
```json
{"events": [{...}, {...}, {...}]}
```

We write one event per line:
```json
{"event": "start", ...}
{"event": "end", ...}
```

**Why?** Because:
- We can write events as they happen (streaming)
- If the power goes out, we don't lose everything
- Easy to read with `grep` and `head`

---

## FAQ 🤷

**Q: Will this slow down my jobs?**
A: No! It adds maybe 10-20 milliseconds per command - that's 0.02 seconds on a 5-minute job.

**Q: Do I need to change my code?**
A: Just wrap your commands with `obsrun` or use `pipewatch run`. No other changes needed.

**Q: Can I use this without SLURM?**
A: Yes! Works on any Linux/Mac computer. SLURM info is just a nice bonus if available.

**Q: What if obsrun fails?**
A: Your original command still runs. The wrapper is designed to never break your pipeline.

**Q: Where are the events saved?**
A: By default, `pipewatch-events.ndjson` in the current folder. Set `PIPEWATCH_EVENTS_FILE` to change it.

---

## Visual Summary 🎨

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR PIPELINE                             │
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                │
│  │  Step 1  │──▶│  Step 2  │──▶│  Step 3  │                │
│  │ (align)  │   │  (sort)  │   │ (markdup)│                │
│  └──────────┘   └──────────┘   └──────────┘                │
│         │             │             │                       │
│         ▼             ▼             ▼                       │
│  ┌────────────────────────────────────────┐                │
│  │     obsrun watches everything          │                │
│  │  • Start time, end time                │                │
│  │  • Memory used                         │                │
│  │  • Exit code (success/fail)            │                │
│  └────────────────────────────────────────┘                │
│                     │                                       │
│                     ▼                                       │
│  ┌────────────────────────────────────────┐                │
│  │   pipewatch-events.ndjson              │                │
│  │   (the diary of what happened)         │                │
│  └────────────────────────────────────────┘                │
│                     │                                       │
│                     ▼                                       │
│  ┌────────────────────────────────────────┐                │
│  │   pipewatch report                     │                │
│  │   (makes pretty HTML report)           │                │
│  └────────────────────────────────────────┘                │
│                     │                                       │
│                     ▼                                       │
│         ┌───────────────────┐                              │
│         │   📊 report.html   │                              │
│         │  • Slowest steps   │                              │
│         │  • Failures        │                              │
│         │  • Memory usage    │                              │
│         └───────────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start (Copy-Paste) 🚀

```bash
# 1. Install
pip install pipewatch

# 2. Try a simple command
obsrun "echo hello world"

# 3. See what was recorded
cat pipewatch-events.ndjson

# 4. Make a report
pipewatch report pipewatch-events.ndjson -o report/

# 5. Open the report
open report/index.html  # Mac
# OR
xdg-open report/index.html  # Linux
```

---

## Need More Help? 💁

- See `README.md` for detailed technical docs
- Check `examples/` folder for real workflows
- Run `pipewatch --help` for all commands

**Remember**: Pipewatch is like a fitness tracker - it doesn't change how you run, it just tells you what happened! 🏃‍♂️📊
