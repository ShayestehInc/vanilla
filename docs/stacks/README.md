# Stack profiles

Every agent in this pipeline reads **`docs/stacks/ACTIVE.md`** for the things
that differ between projects: where the code lives, what the test commands are,
which component library is in play, which providers exist, and the mobile
device matrix.

Pick a profile and make it active:

```bash
cp docs/stacks/django-next.md docs/stacks/ACTIVE.md   # or symlink it
```

Then fill in every `{{placeholder}}` in it. An `ACTIVE.md` that lies is worse
than one that is missing — agents will run the commands it lists.

Profiles here are starting points, not a menu you are limited to. Write a new
one by copying `_template.md`.
