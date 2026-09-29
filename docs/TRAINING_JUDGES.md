# Training judge review

`examples/training.gallos.toml` is a restricted practice profile, not a
contest authorization list. Its 47 exact hostnames came from the Organizer's
candidate list and a public-page review on 2026-09-28. A reachable landing
page or indexed problem catalog supports inclusion; it does **not** prove that
sign-in, submission, every asset, or every redirect works from the Live ISO.
Those flows require graphical acceptance before distribution.

Codeforces' own [emergency-site announcement](https://codeforces.com/blog/entry/63375)
names `m1`, `m2`, and `m3`; its [mirror](https://mirror.codeforces.com/apiHelp)
is also available. They are listed explicitly rather than admitting every
`*.codeforces.com` subdomain. [Kattis](https://open.kattis.com/problems),
[SPOJ](https://www.spoj.com/SPOJ/problems/main/), and
[DMOJ](https://dmoj.ca/problems/) have current problem catalogs even though
their homepages could not be fetched by the review tool.

The following submitted sites were omitted because the review could not
confirm the supplied address or found a legacy redirect. This is an
**unconfirmed** classification, not a claim that every service is offline:

| Submitted site | Host or address awaiting review |
| --- | --- |
| GuiniJuez, POJ, ZOJ, UVALive | `guinijuez.org`, `poj.org`, `pintia.cn/problem-sets/91827364500`, `livearchive.onlinejudge.org` |
| HYSBZ, Z-Trening, UESTC, FZU, CSU, SCU, ACdream | `lydsy.com`, `codah.club`, `cdoj.site`, `acm.fzu.edu.cn`, `acm.csu.edu.cn`, `acm.scu.edu.cn`, `acdream.info` |
| OpenJudge, HihoCoder, HIT, HRBUST, EIJudge | `openjudge.cn`, `hihocoder.com`, `acm.hit.edu.cn`, `acm.hrbust.edu.cn`, `acm.mipt.ru` |
| TopCoder, Jisuanke, CSG, Baekjoon | `arena.topcoder.com`, `nanti.jisuanke.com`, `cpc.csgrandeur.cn`, `acmicpc.net` |
| BZOJ, Daimayuan, ACMP | `new.bzoj.org:88`, `bs.daimayuan.top`, `acmp.ru` |

The training firewall permits the local proxy to contact only listed
HTTP/HTTPS hosts. If a site needs an identity provider or asset host, add
that exact host only after checking its function and recording it here.
Sites that include AI features under an allowed hostname remain a separate
anti-AI policy issue. An Organizer can supply a narrower `gallos.toml` for a
specific session. GallosOS stops the training proxy when leaving restricted
Default/Event mode, including on entry into Contest.
