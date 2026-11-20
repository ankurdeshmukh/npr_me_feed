import datetime as dt
import sys
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_feed as bf  # noqa: E402

DAY = dt.date(2026, 11, 17)
PAGE = """
<h1>Morning Edition for November 17, 2026</h1>
<article class="rundown-segment">
 <h3 class="rundown-segment__title"><a href="https://www.npr.org/2026/11/17/1/a">Senate vote &amp; budget</a></h3>
 <button data-audio='{"title":"Senate vote &amp; budget","audioUrl":"https:\\/\\/ondemand.npr.org\\/anon.npr-mp3\\/npr\\/me\\/2026\\/11\\/20261117_me_senate.mp3?d=240","storyUrl":"https:\\/\\/www.npr.org\\/2026\\/11\\/17\\/1\\/a","duration":240}'></button>
</article>
<article class="rundown-segment">
 <h3 class="rundown-segment__title">Hurricane season wraps</h3>
 <a href="https://ondemand.npr.org/anon.npr-mp3/npr/me/2026/11/20261117_me_hurricane.mp3?size=1">Download</a>
</article>
<a href="https://ondemand.npr.org/anon.npr-mp3/npr/atc/2026/11/20261116_atc_other.mp3">not ME</a>
<a href="https://ondemand.npr.org/anon.npr-mp3/npr/me/2026/11/20261116_me_yesterday.mp3">yesterday</a>
<a href="https://ondemand.npr.org/anon.npr-mp3/npr/me/2026/11/20261117_me_senate.mp3?other=2">dup</a>
"""


def test_parse_and_feed(tmp_path=None):
    s = bf.parse_stories(PAGE, DAY)
    assert [x["title"] for x in s] == ["Senate vote & budget", "Hurricane season wraps"], s
    assert s[0]["duration"] == 240 and "/me/" in s[0]["audio"]
    state = bf.merge([], DAY, s)
    # rerun adds nothing new
    state = bf.merge(state, DAY, s)
    assert len(state) == 2
    assert state[-1]["seq"] == 1  # newest first, so story 1 is last
    rss = bf.build_rss(state, "https://x.github.io/npr-me-feed")
    xml.dom.minidom.parseString(rss)  # well-formed
    assert rss.count("<item>") == 2
    # rollover drops old days
    later = bf.merge(state, DAY + dt.timedelta(days=5), [])
    assert later == []


if __name__ == "__main__":
    test_parse_and_feed()
    print("ok")
