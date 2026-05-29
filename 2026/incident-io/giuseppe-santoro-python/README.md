# On-Call scheduling take-home task

We expect this task to take you about an hour to complete.

Please feel free to use AI coding tools such as Cursor or Claude to complete the
challenge, just as you would in a real-world scenario. However, the expectation is
that you will fully understand the code you submit, and could comfortably explain it
to a colleague or extend it.

Additionally, you can use any libraries that you choose.

## Background

At incident.io, we believe everyone should be on-call by default.

It's also important that you can get 'cover' for parts of your on-call shift,
for example if you want to go for a swim or you've had a bad night and need to
catch up on sleep.

This is a script we use to figure out who was *actually* on-call when, based on 
a list of schedule entries (the original plan) and overrides (when someone
else temporarily took the pager).

## Getting set up

- `pip3 install -r requirements.txt` to ensure you've installed dependencies
- `python3 main.py` to run the script
- `pytest` to run the tests

## The Challenge

We'd like you to 'fill in the blanks' in the script, so that when someone runs
the script it will load the data from `input.json` and then:
1. Check that the schedule entries do not overlap with each other
2. Check that there are no 'gaps' in the schedule (i.e. no time when no one was scheduled to be on-call).
3. Check that the override entries do not overlap with each other
4. Flatten the schedule entries and overrides into a single list of 'entries', that represents who was
   actually on-call at any given time.

### Output

The script should either:
1. Exit with an error if there are any gaps in the schedule, or overlapping overrides
2. Write an `output.json` file in the data directory that contains the flattened list of entries.

### Assumptions

You can assume that:
* The input data structure is valid (JSON is well-formed, dates are in ISO 8601 format, etc.).
* There will be no more than 100 schedule entries or override entries.
* All dates are in UTC.
* Overrides will not extend beyond the start or end of the schedule.

For the purposes of this task, you do not need to consider performance optimisations: we're much more
interested in the structure, correctness and clarity of your code.

## Sending us your solution

Once you've completed the task, please create a zip file containing the modified codebase,
including the `output.json` file that your script generates.

Then, please record a short [Loom](https://www.loom.com/) video of you walking through the code you've
written, explaining how it works and why you made the decisions you did.

Imagine that you're explaining it to a colleague who is not familiar with the codebase, and is being asked
to review your work and maintain it in the future.

This Loom should be about 5 minutes long, and should:
* Walk through the flow of the code
* Explain how the code works, imagining that you're explaining it to a colleague who is not familiar with the domain
* Highlight any assumptions you've made, and why you made them

## Understanding the on-call schedule

An example schedule export can be found in `input.json`.

There are two lists of entries in the data:
- `schedule_entries`: This is a list of periods when a user is scheduled to be on-call. There should
  be no gaps in this list, meaning that one shift starts as the one before it ends.
- `override_entries`: This is a list of periods when a user temporarily takes over the pager from another
  user. These can overlap with the schedule entries, and should be compensated instead of the
  original user.