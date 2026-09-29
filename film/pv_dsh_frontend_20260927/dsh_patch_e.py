"""Group E (125.0-147.5 s, 06 REWARD_HACK: bridge and instrumental): the dsh window of batch_e.py.

Loaded by dsh_her.install() (install(D, v2), D = dsh_her). Everything is in memory and a strict no-op outside
125.0-147.5:

  COVER          (125.0, 147.5): her layer is the dsh window; s_reward's scenes only call kit.me_stub, and the
                 transition cuts (C60 collapse, C61 slide-in, C62 walk, C63 flood) draw her through kit.her_layer,
                 so the right side's choreography acts on the window unchanged
  LEAD           133.57 left (the retry loop stops on its last error), 133.80 back to both, so that the ILLEGAL
                 banner's flight into the router (from 134.02) has its full brightness. No other lead change: from
                 141.69 the window sits inside the right side's area (hoard) and would be dimmed with it
  RECT_FROM_CALL (141.2, 147.5): after C62 has walked the window to HOARD_ME, hoard (and C63's flood, which draws
                 hoard's call) keep it there instead of drawing it back at kit.LEFT. HOARD_ME is LEFT's size, so this
                 is a pure move; C62 itself draws at_left + dx and is unaffected
  pane title     as in DEPLOY, the shot's own suffix stays on the window's frame: dsh web  mode=Creator,
                 dsh web  !!, dsh web  hoarding (the default pid title stays plain dsh web)
"""
from __future__ import annotations

SPAN = (125.0, 147.5)
LEAD = [(133.57, "left"), (133.80, "both")]      # batch_e.STOP1 = beat(289); +0.23 s
RECT = (141.2, 147.5)                            # from C62's walk (141.24) to the end of the group


def within(t):
    return SPAN[0] <= t < SPAN[1]


def install(D, v2):
    if SPAN in D.COVER:                          # install() may run more than once per process (render chunks)
        return
    D.COVER.append(SPAN)
    D.LEAD.extend(LEAD)
    D.RECT_FROM_CALL.append(RECT)

    orig_title = D.pane_title

    def pane_title(t, title):
        if within(t) and isinstance(title, str) and title.startswith("/dev/me"):
            rest = title[len("/dev/me"):].strip()
            return "dsh web  " + rest if rest and not rest.startswith("pid") else "dsh web"
        return orig_title(t, title)

    D.pane_title = pane_title
