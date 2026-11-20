# My Morning Edition: a daily Overcast feed

Every morning, a GitHub job reads today's NPR Morning Edition lineup and
publishes a podcast feed. Each story is one episode, played straight from
NPR's own audio. Stories are numbered (01, 02…) in the order they aired.

## One-time setup (about 10 minutes)

1. **Create a GitHub account** at github.com if you don't have one.
2. **Make a new repository** called `npr-me-feed`. Set it to *Public*,
   because free GitHub Pages needs a public repo. The feed only holds links
   to NPR's audio, not the audio itself.
3. **Upload these files.** On the repo page, click *Add file → Upload files*
   and drag in everything from this folder, including the hidden `.github`
   folder. On a Mac, press **Cmd+Shift+.** in Finder to show hidden folders.
   Then click *Commit changes*.
4. **Turn on Pages:** *Settings → Pages → Build and deployment → Source:
   GitHub Actions*.
5. **Allow the job to save its progress:** *Settings → Actions → General →
   Workflow permissions → Read and write permissions → Save*.
6. **Run it once by hand:** *Actions tab → Build Morning Edition feed → Run
   workflow*. Wait for the green check (about 1 minute). Open the run log to
   see which stories it found.
7. **Subscribe in Overcast:** *+ (Add Podcast) → Add URL*, and paste
   `https://YOUR-GITHUB-USERNAME.github.io/npr-me-feed/feed.xml`

## Overcast tips

- Open the podcast's settings, set **Episode order: Oldest first**, and turn
  on **auto-download**. Story 01 then plays first and each story runs into
  the next.
- For one tap every morning, add the podcast to a playlist and press play
  on that playlist.

## How it runs

- It runs six times between about 4:45 and 6:45 AM Eastern, so the feed is
  ready before 7. Each run only adds stories that weren't in the feed yet.
- Stories from the last 3 days stay in the feed, and older ones drop off.
  To keep more days, set `KEEP_DAYS` in `.github/workflows/daily.yml`.
- To rename the show, change `FEED_TITLE` in the same file.

## If a morning comes up empty

NPR occasionally changes its page layout. If the run log says
`found 0 Morning Edition stories` on a weekday, the page reader in
`build_feed.py` (`parse_stories`) needs an update. Paste the log into Claude
and ask for a fix.
